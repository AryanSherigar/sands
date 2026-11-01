"""Builds a complete corpus: template, playthrough, commitments and lore fill."""

import random
from uuid import uuid4

from app.models.common import SourceKind, TemplateMode
from app.models.facts import EntityRow
from psycopg import AsyncConnection

from scripts import retrieval_latency_playthrough as playthrough
from scripts import retrieval_latency_template as template_content
from scripts.retrieval_latency_types import BuiltCorpus, CorpusSpec, MeasurementError

COUNT_TARGETS_SQL = (
    "SELECT (SELECT count(*) FROM memory_span) + (SELECT count(*) FROM memory_fact)"
)
DESCRIPTION_KINDS: dict[TemplateMode, SourceKind] = {
    "newbie": "authored_card",
    "master": "authored_description",
}
LORE_REF_PREFIX = "lore"


async def count_embeddable_targets(connection: AsyncConnection) -> int:
    cursor = await connection.execute(COUNT_TARGETS_SQL)
    row = await cursor.fetchone()
    if row is None:
        raise MeasurementError("Target count query returned no row.")
    return int(row[0])


async def _resolve_lore_count(connection: AsyncConnection, spec: CorpusSpec) -> int:
    if spec.target_embeddable is None:
        return spec.fixed_lore_count
    current = await count_embeddable_targets(connection)
    lore_count = spec.target_embeddable - current
    if lore_count < 0:
        raise MeasurementError(
            f"{spec.name}: {current} targets already exceed {spec.target_embeddable}."
        )
    return lore_count


async def _store_authored_content(
    connection: AsyncConnection,
    rng: random.Random,
    corpus: BuiltCorpus,
    entities: list[EntityRow],
) -> None:
    kind = DESCRIPTION_KINDS[corpus.spec.mode]
    descriptions = template_content.plan_description_spans(rng, corpus, entities)
    await template_content.store_span_plans(
        connection, corpus.template_id, descriptions, kind, "description"
    )
    facts = template_content.build_relation_facts(rng, corpus, entities)
    facts += template_content.build_attribute_facts(rng, corpus, entities)
    await template_content.insert_facts(connection, facts)


async def _fill_lore(
    connection: AsyncConnection,
    rng: random.Random,
    corpus: BuiltCorpus,
    entities: list[EntityRow],
) -> None:
    lore_count = await _resolve_lore_count(connection, corpus.spec)
    plans = template_content.plan_lore_spans(rng, corpus, entities, lore_count)
    await template_content.store_span_plans(
        connection, corpus.template_id, plans, "authored_lore", LORE_REF_PREFIX
    )


async def build_corpus(
    connection: AsyncConnection, spec: CorpusSpec, rng: random.Random
) -> BuiltCorpus:
    template = await template_content.create_template(connection, spec)
    corpus = BuiltCorpus(spec, template.template_id, uuid4())
    entities = await template_content.create_entities(
        connection, template.template_id, spec.entity_count
    )
    await _store_authored_content(connection, rng, corpus, entities)
    await playthrough.register_and_ingest(connection, rng, corpus, template, entities)
    await playthrough.add_commitments_and_scenes(connection, rng, corpus, entities)
    await _fill_lore(connection, rng, corpus, entities)
    return corpus
