"""Applies a register_playthrough item: template link, player entity, setup facts."""

from dataclasses import dataclass
from uuid import UUID

import structlog
from app.config import get_settings
from app.exceptions.ingest_exceptions import IngestContentConflictError
from app.models.evidence import SourceCreate, SourceRow, SpanDraft, SpanRow
from app.models.facts import (
    AliasCreate,
    EntityCreate,
    EntityRow,
    FactCreate,
    FactRow,
    FactSourceCreate,
)
from app.models.ingest import PlayerEntityPayload, RegisterPayload, SetupFactPayload
from app.models.templates import PlaythroughCreate
from app.repositories import (
    entity_repo,
    fact_repo,
    playthrough_repo,
    source_repo,
    span_repo,
    template_repo,
)
from app.services.accepted_fact_mapper import canonical_value
from app.services.fact_text import render_fact_text
from app.services.ingest_common import (
    OUTCOME_APPLIED,
    OUTCOME_DUPLICATE,
    PLAYTHROUGH_SCOPE,
    TEMPLATE_SCOPE,
    ItemOutcome,
    sha256_hex,
    span_from_draft,
)
from app.services.span_splitter import split_spans
from psycopg import AsyncConnection

logger = structlog.get_logger()

EVENT_SETUP_FACT_DROPPED = "ingest_setup_fact_dropped"
EVENT_REGISTRATION_CONFLICT = "ingest_registration_content_conflict"
REGISTRATION_SOURCE_REF = "registration"
SETUP_SEQUENCE = 0
SETUP_LABEL_PREFIX = f"S{SETUP_SEQUENCE}"
SETUP_PARAGRAPH_SEPARATOR = "\n\n"


@dataclass(frozen=True)
class _SetupLine:
    fact: SetupFactPayload
    start_offset: int
    end_offset: int

    def overlaps(self, start_offset: int, end_offset: int) -> bool:
        return start_offset < self.end_offset and end_offset > self.start_offset


async def apply_register_item(
    connection: AsyncConnection, playthrough_id: UUID, payload: RegisterPayload
) -> ItemOutcome:
    template = await template_repo.get_template_by_revision(
        connection, payload.scenario_id, payload.publish_revision
    )
    template_id = template.template_id if template is not None else None
    template_entities = await _load_template_entities(connection, template_id, payload)
    facts = _resolvable_setup_facts(playthrough_id, payload, template_entities)
    content, lines = _render_setup(facts, _display_names(payload, template_entities))
    registration_hash = sha256_hex(canonical_value(payload.model_dump(mode="json")))
    source, is_inserted = await _store_setup_source(
        connection, playthrough_id, content, registration_hash
    )
    if not is_inserted:
        return _duplicate_or_conflict(playthrough_id, source, registration_hash)
    entity_ids = await _register_player_and_playthrough(
        connection, playthrough_id, template_id, payload, template_entities
    )
    await _write_setup_facts(connection, playthrough_id, source, lines, entity_ids)
    return OUTCOME_APPLIED


async def _register_player_and_playthrough(
    connection: AsyncConnection,
    playthrough_id: UUID,
    template_id: UUID | None,
    payload: RegisterPayload,
    template_entities: dict[UUID, EntityRow],
) -> dict[UUID, UUID]:
    player_entity_id = await _resolve_player(
        connection, playthrough_id, payload.player_entity, template_entities
    )
    await playthrough_repo.register_playthrough(
        connection,
        PlaythroughCreate(
            playthrough_id=playthrough_id,
            template_id=template_id,
            player_entity_id=player_entity_id,
            participants=payload.participants,
            tracked_fields=payload.tracked_fields,
        ),
    )
    return _entity_id_map(template_entities, payload.player_entity, player_entity_id)


def _referenced_authored_ids(payload: RegisterPayload) -> list[UUID]:
    referenced = {fact.subject_entity_id for fact in payload.setup_facts}
    referenced |= {
        fact.object_entity_id
        for fact in payload.setup_facts
        if fact.object_entity_id is not None
    }
    if payload.player_entity is not None:
        referenced.add(payload.player_entity.authored_entity_id)
    return sorted(referenced, key=str)


async def _load_template_entities(
    connection: AsyncConnection, template_id: UUID | None, payload: RegisterPayload
) -> dict[UUID, EntityRow]:
    if template_id is None:
        return {}
    rows = await entity_repo.get_entities_by_authored_ids(
        connection, [(TEMPLATE_SCOPE, template_id)], _referenced_authored_ids(payload)
    )
    return {row.authored_entity_id: row for row in rows if row.authored_entity_id}


def _fact_refs(fact: SetupFactPayload) -> list[UUID]:
    if fact.object_entity_id is None:
        return [fact.subject_entity_id]
    return [fact.subject_entity_id, fact.object_entity_id]


def _resolvable_setup_facts(
    playthrough_id: UUID,
    payload: RegisterPayload,
    template_entities: dict[UUID, EntityRow],
) -> list[SetupFactPayload]:
    resolvable = set(template_entities)
    if payload.player_entity is not None:
        resolvable.add(payload.player_entity.authored_entity_id)
    kept: list[SetupFactPayload] = []
    for fact in payload.setup_facts:
        if all(ref in resolvable for ref in _fact_refs(fact)):
            kept.append(fact)
            continue
        logger.info(
            EVENT_SETUP_FACT_DROPPED,
            playthrough_id=str(playthrough_id),
            fact_id=str(fact.fact_id),
        )
    return kept


def _display_names(
    payload: RegisterPayload, template_entities: dict[UUID, EntityRow]
) -> dict[UUID, str]:
    names = {
        authored_id: row.canonical_name
        for authored_id, row in template_entities.items()
    }
    if payload.player_entity is not None:
        player = payload.player_entity
        names[player.authored_entity_id] = player.canonical_name
    return names


def _render_fact(fact: SetupFactPayload, names: dict[UUID, str]) -> str:
    if fact.object_entity_id is not None:
        object_text = names[fact.object_entity_id]
    else:
        object_text = fact.object_literal or ""
    return render_fact_text(names[fact.subject_entity_id], fact.predicate, object_text)


def _render_setup(
    facts: list[SetupFactPayload], names: dict[UUID, str]
) -> tuple[str, list[_SetupLine]]:
    rendered = [_render_fact(fact, names) for fact in facts]
    lines: list[_SetupLine] = []
    cursor = 0
    for fact, text in zip(facts, rendered, strict=True):
        lines.append(_SetupLine(fact, cursor, cursor + len(text)))
        cursor += len(text) + len(SETUP_PARAGRAPH_SEPARATOR)
    return SETUP_PARAGRAPH_SEPARATOR.join(rendered), lines


async def _store_setup_source(
    connection: AsyncConnection,
    playthrough_id: UUID,
    content: str,
    registration_hash: str,
) -> tuple[SourceRow, bool]:
    source = SourceCreate(
        scope_kind=PLAYTHROUGH_SCOPE,
        scope_id=playthrough_id,
        source_kind="setup",
        source_ref=REGISTRATION_SOURCE_REF,
        sequence=SETUP_SEQUENCE,
        content=content,
        content_hash=registration_hash,
    )
    return await source_repo.create_source_with_status(connection, source)


def _duplicate_or_conflict(
    playthrough_id: UUID, source: SourceRow, registration_hash: str
) -> ItemOutcome:
    if source.content_hash == registration_hash:
        return OUTCOME_DUPLICATE
    logger.warning(
        EVENT_REGISTRATION_CONFLICT,
        playthrough_id=str(playthrough_id),
        sequence=SETUP_SEQUENCE,
    )
    raise IngestContentConflictError(playthrough_id, REGISTRATION_SOURCE_REF)


async def _resolve_player(
    connection: AsyncConnection,
    playthrough_id: UUID,
    player: PlayerEntityPayload | None,
    template_entities: dict[UUID, EntityRow],
) -> UUID | None:
    if player is None:
        return None
    template_player = template_entities.get(player.authored_entity_id)
    if template_player is not None:
        entity_id = template_player.entity_id
    else:
        entity_id = await _create_playthrough_player(connection, playthrough_id, player)
    await entity_repo.add_aliases(
        connection, _player_aliases(entity_id, playthrough_id, player)
    )
    return entity_id


async def _create_playthrough_player(
    connection: AsyncConnection, playthrough_id: UUID, player: PlayerEntityPayload
) -> UUID:
    row = await entity_repo.create_entity(
        connection,
        EntityCreate(
            scope_kind=PLAYTHROUGH_SCOPE,
            scope_id=playthrough_id,
            authored_entity_id=player.authored_entity_id,
            entity_type=player.entity_type,
            canonical_name=player.canonical_name,
            provenance="authored",
            first_seen_seq=SETUP_SEQUENCE,
            is_player=True,
        ),
    )
    return row.entity_id


def _player_aliases(
    entity_id: UUID, playthrough_id: UUID, player: PlayerEntityPayload
) -> list[AliasCreate]:
    by_normalized: dict[str, str] = {}
    for alias in [player.canonical_name, *player.aliases]:
        by_normalized.setdefault(entity_repo.normalize_alias(alias), alias)
    return [
        AliasCreate(
            entity_id=entity_id,
            scope_kind=PLAYTHROUGH_SCOPE,
            scope_id=playthrough_id,
            alias=alias,
            alias_normalized=normalized,
        )
        for normalized, alias in by_normalized.items()
        if normalized
    ]


def _entity_id_map(
    template_entities: dict[UUID, EntityRow],
    player: PlayerEntityPayload | None,
    player_entity_id: UUID | None,
) -> dict[UUID, UUID]:
    entity_ids = {
        authored_id: row.entity_id for authored_id, row in template_entities.items()
    }
    if player is not None and player_entity_id is not None:
        entity_ids[player.authored_entity_id] = player_entity_id
    return entity_ids


async def _write_setup_facts(
    connection: AsyncConnection,
    playthrough_id: UUID,
    source: SourceRow,
    lines: list[_SetupLine],
    entity_ids: dict[UUID, UUID],
) -> None:
    if not lines:
        return
    settings = get_settings()
    drafts = split_spans(
        source.content,
        SETUP_LABEL_PREFIX,
        settings.span_max_tokens,
        settings.span_chars_per_token,
    )
    spans = await span_repo.create_spans(
        connection,
        [
            span_from_draft(source, draft, _draft_entity_ids(draft, lines, entity_ids))
            for draft in drafts
        ],
    )
    facts = await fact_repo.create_facts(
        connection,
        [_setup_fact(playthrough_id, line.fact, entity_ids) for line in lines],
    )
    await fact_repo.add_fact_sources(connection, _fact_span_links(lines, facts, spans))


def _mapped_refs(fact: SetupFactPayload, entity_ids: dict[UUID, UUID]) -> list[UUID]:
    return [entity_ids[ref] for ref in _fact_refs(fact)]


def _draft_entity_ids(
    draft: SpanDraft, lines: list[_SetupLine], entity_ids: dict[UUID, UUID]
) -> list[UUID]:
    matched = {
        entity_id
        for line in lines
        if line.overlaps(draft.start_offset, draft.end_offset)
        for entity_id in _mapped_refs(line.fact, entity_ids)
    }
    return sorted(matched, key=str)


def _setup_fact(
    playthrough_id: UUID, fact: SetupFactPayload, entity_ids: dict[UUID, UUID]
) -> FactCreate:
    object_entity_id = None
    if fact.object_entity_id is not None:
        object_entity_id = entity_ids[fact.object_entity_id]
    return FactCreate(
        scope_kind=PLAYTHROUGH_SCOPE,
        scope_id=playthrough_id,
        subject_entity_id=entity_ids[fact.subject_entity_id],
        predicate=fact.predicate,
        object_entity_id=object_entity_id,
        object_literal=fact.object_literal,
        authority="accepted",
        assertion="occurred",
        valid_from_seq=SETUP_SEQUENCE,
    )


def _fact_span_links(
    lines: list[_SetupLine], facts: list[FactRow], spans: list[SpanRow]
) -> list[FactSourceCreate]:
    return [
        FactSourceCreate(fact_id=fact.fact_id, span_id=span.span_id)
        for line, fact in zip(lines, facts, strict=True)
        for span in spans
        if line.overlaps(span.start_offset, span.end_offset)
    ]
