"""Writes one turn's sources, spans, events and accepted facts."""

from dataclasses import dataclass
from uuid import UUID

import structlog
from app.config import get_settings
from app.exceptions.ingest_exceptions import IngestContentConflictError
from app.models.common import EventKind, SourceKind
from app.models.evidence import (
    EventCreate,
    SourceCreate,
    SourceRow,
    SpanCreate,
    SpanDraft,
)
from app.models.ingest import TurnPayload
from app.repositories import event_repo, source_repo, span_repo
from app.services.accepted_fact_ingest import apply_accepted_mutation
from app.services.accepted_roll_ingest import apply_accepted_roll
from app.services.entity_tagger import tag_entities
from app.services.ingest_common import (
    OUTCOME_APPLIED,
    OUTCOME_DUPLICATE,
    PLAYTHROUGH_SCOPE,
    ItemOutcome,
    TurnContext,
    sha256_hex,
    span_from_draft,
)
from app.services.span_splitter import split_spans

logger = structlog.get_logger()

EVENT_CONTENT_CONFLICT = "ingest_turn_content_conflict"
NARRATION_KIND: SourceKind = "turn_narration"
ACTION_KIND: SourceKind = "turn_action"
REJECTED_EVENT_KIND: EventKind = "rejected_mutation"
FACT_MUTATION_KINDS = frozenset(("state_mutation", "automatic_effect"))
ROLL_KIND = "roll"


@dataclass(frozen=True)
class _StoredSource:
    row: SourceRow
    is_inserted: bool
    expected_hash: str

    def conflicts(self, is_new_turn: bool) -> bool:
        if self.is_inserted:
            return not is_new_turn
        return self.row.content_hash != self.expected_hash


async def apply_turn_item(context: TurnContext, payload: TurnPayload) -> ItemOutcome:
    narration = await _store_source(context, payload, NARRATION_KIND, None)
    stored = [narration]
    if payload.action_text:
        stored.insert(
            0,
            await _store_source(context, payload, ACTION_KIND, payload.participant_id),
        )
    is_new_turn = narration.is_inserted
    has_conflict = any(source.conflicts(is_new_turn) for source in stored)
    if has_conflict or await _has_dropped_action(context, payload, is_new_turn):
        _raise_conflict(context, payload)
    if not is_new_turn:
        return OUTCOME_DUPLICATE
    await _write_spans(context, payload.turn_number, [source.row for source in stored])
    await _write_events_and_facts(context, payload)
    return OUTCOME_APPLIED


async def _has_dropped_action(
    context: TurnContext, payload: TurnPayload, is_new_turn: bool
) -> bool:
    if is_new_turn or payload.action_text:
        return False
    stored_action = await source_repo.get_source_by_ref(
        context.connection,
        PLAYTHROUGH_SCOPE,
        context.playthrough_id,
        ACTION_KIND,
        str(payload.turn_id),
    )
    return stored_action is not None


def _raise_conflict(context: TurnContext, payload: TurnPayload) -> None:
    logger.warning(
        EVENT_CONTENT_CONFLICT,
        playthrough_id=str(context.playthrough_id),
        sequence=payload.turn_number,
    )
    raise IngestContentConflictError(context.playthrough_id, str(payload.turn_id))


def _source_content(payload: TurnPayload, source_kind: SourceKind) -> str:
    if source_kind == ACTION_KIND:
        return payload.action_text
    return payload.narration_text


async def _store_source(
    context: TurnContext,
    payload: TurnPayload,
    source_kind: SourceKind,
    actor_participant_id: UUID | None,
) -> _StoredSource:
    content = _source_content(payload, source_kind)
    content_hash = sha256_hex(content)
    source = SourceCreate(
        scope_kind=PLAYTHROUGH_SCOPE,
        scope_id=context.playthrough_id,
        source_kind=source_kind,
        source_ref=str(payload.turn_id),
        sequence=payload.turn_number,
        actor_participant_id=actor_participant_id,
        content=content,
        content_hash=content_hash,
    )
    row, is_inserted = await source_repo.create_source_with_status(
        context.connection, source
    )
    return _StoredSource(row, is_inserted, content_hash)


async def _write_spans(
    context: TurnContext, sequence: int, sources: list[SourceRow]
) -> None:
    settings = get_settings()
    label_prefix = f"S{sequence}"
    spans: list[SpanCreate] = []
    for source in sources:
        drafts = split_spans(
            source.content,
            label_prefix,
            settings.span_max_tokens,
            settings.span_chars_per_token,
        )
        continued = [
            _continue_ordinal(draft, len(spans), label_prefix) for draft in drafts
        ]
        spans.extend(_tagged_span(context, source, draft) for draft in continued)
    await span_repo.create_spans(context.connection, spans)


def _continue_ordinal(draft: SpanDraft, offset: int, label_prefix: str) -> SpanDraft:
    ordinal = draft.ordinal + offset
    return draft.model_copy(
        update={"ordinal": ordinal, "label": f"{label_prefix}.{ordinal}"}
    )


def _tagged_span(
    context: TurnContext, source: SourceRow, draft: SpanDraft
) -> SpanCreate:
    return span_from_draft(source, draft, tag_entities(draft.text, context.alias_index))


def _build_events(context: TurnContext, payload: TurnPayload) -> list[EventCreate]:
    accepted = [
        _event(context, payload, item.kind, item.key, item.model_dump(mode="json"))
        for item in payload.accepted_delta.items
    ]
    rejected = [
        _event(
            context,
            payload,
            REJECTED_EVENT_KIND,
            f"rejected:{index}",
            call.model_dump(mode="json"),
        )
        for index, call in enumerate(payload.rejected_calls)
    ]
    return accepted + rejected


def _event(
    context: TurnContext,
    payload: TurnPayload,
    event_kind: EventKind,
    event_key: str,
    event_payload: dict[str, object],
) -> EventCreate:
    return EventCreate(
        playthrough_id=context.playthrough_id,
        sequence=payload.turn_number,
        turn_id=payload.turn_id,
        event_kind=event_kind,
        event_key=event_key,
        is_accepted=event_kind != REJECTED_EVENT_KIND,
        payload=event_payload,
        actor_participant_id=payload.participant_id,
    )


async def _write_events_and_facts(context: TurnContext, payload: TurnPayload) -> None:
    results = await event_repo.create_events_with_status(
        context.connection, _build_events(context, payload)
    )
    accepted_items = payload.accepted_delta.items
    for item, (event, is_inserted) in zip(accepted_items, results, strict=False):
        if not is_inserted:
            continue
        if item.kind in FACT_MUTATION_KINDS:
            await apply_accepted_mutation(context, event, item)
        elif item.kind == ROLL_KIND:
            await apply_accepted_roll(context, event, item)
