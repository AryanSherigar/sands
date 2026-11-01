"""Turns locked outbox rows into memory ingest items.

Pure computation: no I/O, so the row-to-item rules are testable without a
database or an HTTP client.
"""

from dataclasses import dataclass, field
from uuid import UUID

from app.db.models.memory_outbox import (
    ITEM_KIND_FLUSH,
    ITEM_KIND_PARTICIPANTS,
    ITEM_KIND_REGISTER,
    MemoryOutbox,
)
from app.db.models.turn_log import TurnLog
from app.exceptions.memory_exceptions import (
    CODE_PARTICIPANT_MISSING,
    CODE_TURN_LOG_MISSING,
    InvalidOutboxPayloadError,
)
from app.models.accepted_delta import AcceptedDelta
from app.models.memory_ingest import (
    FlushItem,
    IngestItem,
    ParticipantsItem,
    ParticipantsPayload,
    RegisterItem,
    RegisterPayload,
    RejectedCall,
    TurnItem,
    TurnPayload,
)
from app.models.tool_call import MUTATION_TOOL_NAMES
from pydantic import ValidationError


@dataclass(frozen=True)
class RelayBatch:
    """Items to send plus rows that can never be sent, each with its reason."""

    items: list[IngestItem] = field(default_factory=list)
    sendable_row_ids: list[int] = field(default_factory=list)
    orphan_rows: list[tuple[int, str]] = field(default_factory=list)


def build_relay_batch(
    rows: list[MemoryOutbox], turn_logs_by_id: dict[UUID, TurnLog]
) -> RelayBatch:
    """Build the batch for rows already in delivery order.

    Raises InvalidOutboxPayloadError when a row's stored data is malformed.
    """
    items: list[IngestItem] = []
    sendable_row_ids: list[int] = []
    orphan_rows: list[tuple[int, str]] = []
    for row in rows:
        item, orphan_reason = _item_for(row, turn_logs_by_id)
        if item is None:
            orphan_rows.append((row.outbox_id, orphan_reason))
            continue
        items.append(item)
        sendable_row_ids.append(row.outbox_id)
    return RelayBatch(items, sendable_row_ids, orphan_rows)


def _item_for(
    row: MemoryOutbox, turn_logs_by_id: dict[UUID, TurnLog]
) -> tuple[IngestItem | None, str]:
    if row.item_kind == ITEM_KIND_REGISTER:
        return RegisterItem(payload=_register_payload(row)), ""
    if row.item_kind == ITEM_KIND_PARTICIPANTS:
        return _participants_item(row), ""
    if row.item_kind == ITEM_KIND_FLUSH:
        return FlushItem(sequence=row.sequence), ""
    return _turn_item(row, turn_logs_by_id.get(row.turn_id))


def _participants_item(row: MemoryOutbox) -> ParticipantsItem:
    try:
        payload = ParticipantsPayload.model_validate(row.payload)
    except ValidationError as exc:
        raise InvalidOutboxPayloadError() from exc
    return ParticipantsItem(sequence=row.sequence, payload=payload)


def _register_payload(row: MemoryOutbox) -> RegisterPayload:
    try:
        return RegisterPayload.model_validate(row.payload)
    except ValidationError as exc:
        raise InvalidOutboxPayloadError() from exc


def _turn_item(
    row: MemoryOutbox, turn_log: TurnLog | None
) -> tuple[TurnItem | None, str]:
    if turn_log is None:
        return None, CODE_TURN_LOG_MISSING
    if turn_log.participant_id is None:
        return None, CODE_PARTICIPANT_MISSING
    return TurnItem(sequence=row.sequence, payload=_turn_payload(turn_log)), ""


def _turn_payload(turn_log: TurnLog) -> TurnPayload:
    try:
        return TurnPayload(
            turn_id=turn_log.turn_id,
            turn_number=turn_log.turn_number,
            participant_id=turn_log.participant_id,
            action_mode=turn_log.action_mode,
            action_text=turn_log.action_text,
            narration_text=turn_log.narration_text or "",
            accepted_delta=AcceptedDelta.model_validate(turn_log.accepted_delta or {}),
            rejected_calls=_rejected_calls(turn_log.tool_calls),
            created_at=turn_log.created_at,
        )
    except ValidationError as exc:
        raise InvalidOutboxPayloadError() from exc


def _rejected_calls(tool_calls: list[object]) -> list[RejectedCall]:
    rejected: list[RejectedCall] = []
    for call in tool_calls:
        if _is_rejected_mutation(call):
            rejected.append(
                RejectedCall(
                    tool_name=call["tool_name"],
                    arguments=call.get("arguments") or {},
                    result=call.get("result") or {},
                )
            )
    return rejected


def _is_rejected_mutation(call: object) -> bool:
    return (
        isinstance(call, dict)
        and call.get("is_valid") is False
        and call.get("tool_name") in MUTATION_TOOL_NAMES
    )
