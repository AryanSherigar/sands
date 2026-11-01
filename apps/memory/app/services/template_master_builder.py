"""Pure builders for a master template: entities, aliases, descriptions and facts."""

from dataclasses import dataclass
from uuid import UUID

from app.models.facts import AliasCreate, EntityCreate, FactCreate
from app.models.templates import (
    MasterTemplateContent,
    TemplateConnectionPayload,
    TemplateEntityPayload,
    TemplateFactPayload,
)
from app.repositories.entity_repo import normalize_alias
from app.services.fact_text import render_fact_text
from app.services.ingest_common import TEMPLATE_SCOPE
from app.services.span_splitter import split_spans
from app.services.template_plans import FactPlan, SourcePlan, SpanLimits, SpanPlan

AUTHORED_SEQUENCE = 0
CONNECTS_TO_PREDICATE = "connects_to"
DESCRIPTION_LABEL_PREFIX = "D"
FACT_LABEL_PREFIX = "F"


@dataclass(frozen=True)
class _FactContext:
    template_id: UUID
    entity_ids: dict[UUID, UUID]
    names: dict[UUID, str]
    limits: SpanLimits


def build_entity_creates(
    template_id: UUID, content: MasterTemplateContent
) -> list[EntityCreate]:
    return [
        EntityCreate(
            scope_kind=TEMPLATE_SCOPE,
            scope_id=template_id,
            authored_entity_id=entity.entity_id,
            entity_type=entity.entity_type,
            canonical_name=entity.canonical_name,
            provenance="authored",
            first_seen_seq=AUTHORED_SEQUENCE,
            is_player=entity.is_player,
        )
        for entity in content.entities
    ]


def build_alias_creates(
    template_id: UUID, content: MasterTemplateContent, entity_ids: dict[UUID, UUID]
) -> list[AliasCreate]:
    rows: list[AliasCreate] = []
    for entity in content.entities:
        rows.extend(_entity_aliases(template_id, entity, entity_ids[entity.entity_id]))
    return rows


def _entity_aliases(
    template_id: UUID, entity: TemplateEntityPayload, memory_entity_id: UUID
) -> list[AliasCreate]:
    seen: set[str] = set()
    rows: list[AliasCreate] = []
    for alias in [entity.canonical_name, *entity.aliases]:
        normalized = normalize_alias(alias)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        rows.append(
            AliasCreate(
                entity_id=memory_entity_id,
                scope_kind=TEMPLATE_SCOPE,
                scope_id=template_id,
                alias=alias,
                alias_normalized=normalized,
            )
        )
    return rows


def build_description_sources(
    content: MasterTemplateContent, entity_ids: dict[UUID, UUID], limits: SpanLimits
) -> list[SourcePlan]:
    plans: list[SourcePlan] = []
    for index, entity in enumerate(content.entities, start=1):
        description = entity.description or ""
        if not description.strip():
            continue
        drafts = split_spans(
            description,
            f"{DESCRIPTION_LABEL_PREFIX}{index}",
            limits.max_tokens,
            limits.chars_per_token,
        )
        memory_entity_id = entity_ids[entity.entity_id]
        spans = [
            SpanPlan(draft=draft, entity_ids=[memory_entity_id]) for draft in drafts
        ]
        plans.append(
            SourcePlan(
                "authored_description", str(entity.entity_id), description, spans
            )
        )
    return plans


def build_fact_plans(
    template_id: UUID,
    content: MasterTemplateContent,
    entity_ids: dict[UUID, UUID],
    limits: SpanLimits,
) -> list[FactPlan]:
    names = {entity.entity_id: entity.canonical_name for entity in content.entities}
    context = _FactContext(template_id, entity_ids, names, limits)
    plans = [
        _authored_fact_plan(context, number, fact)
        for number, fact in enumerate(content.facts, start=1)
    ]
    first_connection_number = len(content.facts) + 1
    plans.extend(
        _connection_fact_plan(context, number, connection)
        for number, connection in enumerate(
            content.map_connections, start=first_connection_number
        )
    )
    return plans


def _authored_fact_plan(
    context: _FactContext, number: int, fact: TemplateFactPayload
) -> FactPlan:
    if fact.object_entity_id is not None:
        object_text = context.names[fact.object_entity_id]
    else:
        object_text = fact.object_literal or ""
    text = render_fact_text(
        context.names[fact.subject_entity_id], fact.predicate, object_text
    )
    row = _authored_fact_row(
        context,
        subject_id=fact.subject_entity_id,
        predicate=fact.predicate,
        object_id=fact.object_entity_id,
        authored_fact_id=fact.fact_id,
    )
    row = row.model_copy(
        update={
            "object_literal": fact.object_literal,
            "is_hidden": fact.hidden,
            "conditional": fact.when_active is not None,
            "supersedes_authored_fact_id": fact.superseded_fact_id,
        }
    )
    return FactPlan(row, _fact_source(context, number, text, row))


def _connection_fact_plan(
    context: _FactContext, number: int, connection: TemplateConnectionPayload
) -> FactPlan:
    text = render_fact_text(
        context.names[connection.entity_id_a],
        CONNECTS_TO_PREDICATE,
        context.names[connection.entity_id_b],
    )
    if connection.label and connection.label.strip():
        text = f"{text} ({connection.label.strip()})"
    row = _authored_fact_row(
        context,
        subject_id=connection.entity_id_a,
        predicate=CONNECTS_TO_PREDICATE,
        object_id=connection.entity_id_b,
        authored_fact_id=connection.connection_id,
    )
    return FactPlan(row, _fact_source(context, number, text, row))


def _authored_fact_row(
    context: _FactContext,
    *,
    subject_id: UUID,
    predicate: str,
    object_id: UUID | None,
    authored_fact_id: UUID,
) -> FactCreate:
    object_entity_id = context.entity_ids[object_id] if object_id is not None else None
    return FactCreate(
        scope_kind=TEMPLATE_SCOPE,
        scope_id=context.template_id,
        subject_entity_id=context.entity_ids[subject_id],
        predicate=predicate,
        object_entity_id=object_entity_id,
        authority="authored",
        assertion="occurred",
        valid_from_seq=AUTHORED_SEQUENCE,
        authored_fact_id=authored_fact_id,
    )


def _fact_source(
    context: _FactContext, number: int, text: str, row: FactCreate
) -> SourcePlan:
    drafts = split_spans(
        text,
        f"{FACT_LABEL_PREFIX}{number}",
        context.limits.max_tokens,
        context.limits.chars_per_token,
    )
    entity_ids = [row.subject_entity_id]
    if row.object_entity_id is not None and row.object_entity_id != entity_ids[0]:
        entity_ids.append(row.object_entity_id)
    spans = [
        SpanPlan(
            draft=draft,
            entity_ids=entity_ids,
            is_hidden=row.is_hidden,
            conditional=row.conditional,
            authored_fact_id=row.authored_fact_id,
        )
        for draft in drafts
    ]
    return SourcePlan("authored_fact_text", str(row.authored_fact_id), text, spans)
