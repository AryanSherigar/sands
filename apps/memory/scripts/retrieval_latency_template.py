"""Bulk template content: entities, aliases, facts and authored spans."""

import hashlib
import random
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.models.common import SourceKind
from app.models.evidence import SourceCreate, SpanCreate
from app.models.facts import AliasCreate, EntityCreate, EntityRow, FactCreate
from app.models.templates import TemplateCreate, TemplateRow
from app.repositories import (
    entity_repo,
    fact_repo,
    source_repo,
    span_repo,
    template_repo,
)
from psycopg import AsyncConnection

from scripts import retrieval_latency_text as text
from scripts.retrieval_latency_types import (
    BuiltCorpus,
    CorpusSpec,
    Flags,
    draw_flags,
)

PUBLISH_REVISION = 1
SPANS_PER_SOURCE = 25
FACT_INSERT_CHUNK = 500
HUB_DEGREE = 60
SPAN_SEPARATOR = "\n\n"
CONTENT_HASH = "latency"
MIN_MENTIONS = 1
MAX_MENTIONS = 3


@dataclass(frozen=True)
class SpanPlan:
    body: str
    entity_ids: list[UUID]
    flags: Flags


async def create_template(connection: AsyncConnection, spec: CorpusSpec) -> TemplateRow:
    return await template_repo.create_template(
        connection,
        TemplateCreate(
            scenario_id=uuid4(),
            publish_revision=PUBLISH_REVISION,
            mode=spec.mode,
            direct_status="ready",
            enrichment_status="not_needed",
            content_hash=CONTENT_HASH,
        ),
    )


def _entity_create(
    template_id: UUID, index: int, name: text.EntityName
) -> EntityCreate:
    return EntityCreate(
        scope_kind="template",
        scope_id=template_id,
        authored_entity_id=uuid4(),
        entity_type=name.entity_type,
        canonical_name=name.canonical,
        provenance="authored",
        first_seen_seq=0,
        is_player=index == 0,
    )


def _alias_creates(
    template_id: UUID, entity: EntityRow, name: text.EntityName
) -> list[AliasCreate]:
    return [
        AliasCreate(
            entity_id=entity.entity_id,
            scope_kind="template",
            scope_id=template_id,
            alias=alias,
            alias_normalized=entity_repo.normalize_alias(alias),
        )
        for alias in (name.canonical, *name.aliases)
    ]


async def create_entities(
    connection: AsyncConnection, template_id: UUID, count: int
) -> list[EntityRow]:
    entities: list[EntityRow] = []
    for index in range(count):
        name = text.build_entity_name(index)
        entity = await entity_repo.create_entity(
            connection, _entity_create(template_id, index, name)
        )
        await entity_repo.add_aliases(
            connection, _alias_creates(template_id, entity, name)
        )
        entities.append(entity)
    await connection.commit()
    return entities


def plan_relation_edges(
    rng: random.Random, entity_count: int, edge_count: int, hub_count: int
) -> list[tuple[int, int]]:
    """Hub spokes first so hubs exceed the hub edge cap, then a chain that keeps the
    graph connected, then random edges up to `edge_count`."""
    edges: list[tuple[int, int]] = []
    for hub in range(hub_count):
        spokes = rng.sample(range(hub_count, entity_count), HUB_DEGREE)
        edges.extend((hub, spoke) for spoke in spokes)
    edges.extend((index, index + 1) for index in range(entity_count - 1))
    while len(edges) < edge_count:
        subject, target = rng.sample(range(entity_count), 2)
        edges.append((subject, target))
    return edges[:edge_count]


def _fact(
    corpus: BuiltCorpus, subject: EntityRow, flags: Flags, predicate: str
) -> FactCreate:
    return FactCreate(
        scope_kind="template",
        scope_id=corpus.template_id,
        subject_entity_id=subject.entity_id,
        predicate=predicate,
        authority="authored",
        assertion="occurred",
        valid_from_seq=0,
        authored_fact_id=flags.authored_fact_id,
        is_hidden=flags.is_hidden,
        conditional=flags.conditional,
    )


def build_relation_facts(
    rng: random.Random, corpus: BuiltCorpus, entities: list[EntityRow]
) -> list[FactCreate]:
    spec = corpus.spec
    edges = plan_relation_edges(
        rng, len(entities), spec.relation_fact_count, spec.hub_count
    )
    facts = []
    for subject_index, object_index in edges:
        predicate = rng.choice(text.RELATION_PREDICATES)
        fact = _fact(
            corpus, entities[subject_index], draw_flags(rng, corpus), predicate
        )
        fact.object_entity_id = entities[object_index].entity_id
        facts.append(fact)
    return facts


def build_attribute_facts(
    rng: random.Random, corpus: BuiltCorpus, entities: list[EntityRow]
) -> list[FactCreate]:
    facts = []
    for _ in range(corpus.spec.attribute_fact_count):
        predicate = rng.choice(text.ATTRIBUTE_PREDICATES)
        fact = _fact(corpus, rng.choice(entities), draw_flags(rng, corpus), predicate)
        fact.object_literal = text.attribute_value(rng)
        facts.append(fact)
    return facts


async def insert_facts(connection: AsyncConnection, facts: list[FactCreate]) -> None:
    for start in range(0, len(facts), FACT_INSERT_CHUNK):
        chunk = facts[start : start + FACT_INSERT_CHUNK]
        await fact_repo.create_facts(connection, chunk)
    await connection.commit()


def _span_creates(
    source_id: UUID, template_id: UUID, plans: list[SpanPlan]
) -> list[SpanCreate]:
    spans = []
    offset = 0
    for ordinal, plan in enumerate(plans):
        end = offset + len(plan.body)
        spans.append(
            SpanCreate(
                source_id=source_id,
                scope_kind="template",
                scope_id=template_id,
                sequence=0,
                ordinal=ordinal,
                start_offset=offset,
                end_offset=end,
                text=plan.body,
                token_count=len(plan.body.split()),
                label=f"T.{source_id.hex[:8]}.{ordinal}",
                entity_ids=plan.entity_ids,
                is_hidden=plan.flags.is_hidden,
                authored_fact_id=plan.flags.authored_fact_id,
                conditional=plan.flags.conditional,
            )
        )
        offset = end + len(SPAN_SEPARATOR)
    return spans


async def _store_span_group(
    connection: AsyncConnection,
    template_id: UUID,
    plans: list[SpanPlan],
    source_kind: SourceKind,
    source_ref: str,
) -> None:
    content = SPAN_SEPARATOR.join(plan.body for plan in plans)
    source = await source_repo.create_source(
        connection,
        SourceCreate(
            scope_kind="template",
            scope_id=template_id,
            source_kind=source_kind,
            source_ref=source_ref,
            sequence=0,
            content=content,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
        ),
    )
    spans = _span_creates(source.source_id, template_id, plans)
    await span_repo.create_spans(connection, spans)


async def store_span_plans(
    connection: AsyncConnection,
    template_id: UUID,
    plans: list[SpanPlan],
    source_kind: SourceKind,
    ref_prefix: str,
) -> None:
    for group, start in enumerate(range(0, len(plans), SPANS_PER_SOURCE)):
        chunk = plans[start : start + SPANS_PER_SOURCE]
        ref = f"{ref_prefix}-{group}"
        await _store_span_group(connection, template_id, chunk, source_kind, ref)
    await connection.commit()


def plan_description_spans(
    rng: random.Random, corpus: BuiltCorpus, entities: list[EntityRow]
) -> list[SpanPlan]:
    return [
        SpanPlan(
            body=text.lore_paragraph(rng, [entity.canonical_name]),
            entity_ids=[entity.entity_id],
            flags=draw_flags(rng, corpus),
        )
        for entity in entities
    ]


def plan_lore_spans(
    rng: random.Random, corpus: BuiltCorpus, entities: list[EntityRow], count: int
) -> list[SpanPlan]:
    plans = []
    for _ in range(count):
        mentioned = rng.sample(entities, rng.randint(MIN_MENTIONS, MAX_MENTIONS))
        names = [each.canonical_name for each in mentioned]
        plans.append(
            SpanPlan(
                body=text.lore_paragraph(rng, names),
                entity_ids=[each.entity_id for each in mentioned],
                flags=draw_flags(rng, corpus),
            )
        )
    return plans
