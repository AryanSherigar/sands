"""Idempotent ingest of registration, turn and flush items in one transaction."""

import json
import time
from dataclasses import dataclass
from itertools import pairwise
from typing import Annotated
from uuid import UUID

import structlog
from app.config import get_settings
from app.db.pool import get_connection
from app.exceptions.ingest_exceptions import (
    IngestBatchTooLargeError,
    IngestContentConflictError,
    IngestOrderError,
    PlaythroughNotRegisteredError,
    PlaythroughPurgedError,
)
from app.models.ingest import (
    ITEM_KIND_ORDER,
    FlushItem,
    IngestItem,
    IngestItemOutcome,
    IngestRequest,
    IngestResponse,
    ParticipantsItem,
    RegisterItem,
    TurnItem,
)
from app.models.templates import PlaythroughRow
from app.repositories import (
    entity_repo,
    ingest_delivery_repo,
    playthrough_repo,
    source_repo,
)
from app.services.entity_tagger import build_alias_index
from app.services.ingest_common import (
    OUTCOME_APPLIED,
    OUTCOME_DUPLICATE,
    PLAYTHROUGH_SCOPE,
    ItemOutcome,
    TurnContext,
    memory_scopes,
    sha256_hex,
)
from app.services.participants_ingest import apply_participants_item
from app.services.registration_ingest import apply_register_item
from app.services.turn_ingest import NARRATION_KIND, apply_turn_item
from fastapi import Depends
from psycopg import AsyncConnection

logger = structlog.get_logger()

EVENT_INGEST_APPLIED = "ingest_items_applied"
NO_TURN_SEQUENCE = 0
MILLISECONDS_PER_SECOND = 1000


@dataclass
class _RequestState:
    playthrough: PlaythroughRow | None
    alias_index: dict[str, set[UUID]] | None = None


def _validate_items(items: list[IngestItem]) -> None:
    limit = get_settings().ingest_max_items_per_request
    if len(items) > limit:
        raise IngestBatchTooLargeError(limit)
    keys = [(item.sequence, ITEM_KIND_ORDER[item.item_kind]) for item in items]
    if any(earlier >= later for earlier, later in pairwise(keys)):
        raise IngestOrderError()


def _require_registered(playthrough_id: UUID, state: _RequestState) -> PlaythroughRow:
    if state.playthrough is None:
        raise PlaythroughNotRegisteredError(playthrough_id)
    return state.playthrough


def _delivery_payload_hash(request: IngestRequest) -> str:
    payload = request.model_dump(mode="json", exclude={"delivery_id"})
    return sha256_hex(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _duplicate_outcomes(request: IngestRequest) -> list[IngestItemOutcome]:
    return [
        IngestItemOutcome(
            item_kind=item.item_kind, sequence=item.sequence, outcome=OUTCOME_DUPLICATE
        )
        for item in request.items
    ]


class IngestService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def ingest_items(self, request: IngestRequest) -> IngestResponse:
        """Apply every item atomically; any error rolls back the whole request."""
        _validate_items(request.items)
        started = time.monotonic()
        async with self._connection.transaction():
            await ingest_delivery_repo.lock_ingestion(
                self._connection, request.playthrough_id
            )
            if await ingest_delivery_repo.is_purged(
                self._connection, request.playthrough_id
            ):
                raise PlaythroughPurgedError(request.playthrough_id)
            outcomes, row = await self._apply_delivery(request)
        _log_request(row, outcomes, started)
        return IngestResponse(
            playthrough_id=row.playthrough_id,
            ingested_seq=row.ingested_seq,
            latest_seq_seen=row.latest_seq_seen,
            items=outcomes,
        )

    async def _apply_delivery(
        self, request: IngestRequest
    ) -> tuple[list[IngestItemOutcome], PlaythroughRow]:
        payload_hash = _delivery_payload_hash(request)
        if await self._is_duplicate_delivery(request, payload_hash):
            row = await playthrough_repo.get_playthrough(
                self._connection, request.playthrough_id
            )
            if row is None:
                raise PlaythroughNotRegisteredError(request.playthrough_id)
            outcomes = _duplicate_outcomes(request)
            return outcomes, row
        outcomes = await self._apply_items(request)
        row = await self._advance_watermarks(request)
        if request.delivery_id is not None:
            await ingest_delivery_repo.record_delivery(
                self._connection,
                request.playthrough_id,
                request.delivery_id,
                payload_hash,
            )
        return outcomes, row

    async def _is_duplicate_delivery(
        self, request: IngestRequest, payload_hash: str
    ) -> bool:
        if request.delivery_id is None:
            return False
        stored = await ingest_delivery_repo.get_payload_hash(
            self._connection, request.playthrough_id, request.delivery_id
        )
        if stored is not None and stored != payload_hash:
            raise IngestContentConflictError(
                request.playthrough_id, str(request.delivery_id)
            )
        return stored is not None

    async def _apply_items(self, request: IngestRequest) -> list[IngestItemOutcome]:
        playthrough = await playthrough_repo.get_playthrough(
            self._connection, request.playthrough_id
        )
        state = _RequestState(playthrough)
        outcomes: list[IngestItemOutcome] = []
        for item in request.items:
            outcome = await self._apply_item(request.playthrough_id, item, state)
            outcomes.append(
                IngestItemOutcome(
                    item_kind=item.item_kind, sequence=item.sequence, outcome=outcome
                )
            )
        return outcomes

    async def _apply_item(
        self, playthrough_id: UUID, item: IngestItem, state: _RequestState
    ) -> ItemOutcome:
        if isinstance(item, RegisterItem):
            return await self._apply_register(playthrough_id, item, state)
        playthrough = _require_registered(playthrough_id, state)
        if isinstance(item, TurnItem):
            return await self._apply_turn(playthrough, item, state)
        if isinstance(item, ParticipantsItem):
            return await apply_participants_item(
                self._connection, playthrough_id, item.payload
            )
        return await self._apply_flush(playthrough, item, state)

    async def _apply_register(
        self, playthrough_id: UUID, item: RegisterItem, state: _RequestState
    ) -> ItemOutcome:
        outcome = await apply_register_item(
            self._connection, playthrough_id, item.payload
        )
        state.playthrough = await playthrough_repo.get_playthrough(
            self._connection, playthrough_id
        )
        state.alias_index = None
        return outcome

    async def _apply_turn(
        self, playthrough: PlaythroughRow, item: TurnItem, state: _RequestState
    ) -> ItemOutcome:
        if state.alias_index is None:
            state.alias_index = await self._load_alias_index(playthrough)
        context = TurnContext(
            connection=self._connection,
            playthrough_id=playthrough.playthrough_id,
            template_id=playthrough.template_id,
            alias_index=state.alias_index,
        )
        return await apply_turn_item(context, item.payload)

    async def _load_alias_index(
        self, playthrough: PlaythroughRow
    ) -> dict[str, set[UUID]]:
        scopes = memory_scopes(playthrough.playthrough_id, playthrough.template_id)
        aliases = await entity_repo.list_aliases_in_scopes(self._connection, scopes)
        return build_alias_index(aliases)

    async def _apply_flush(
        self, playthrough: PlaythroughRow, item: FlushItem, state: _RequestState
    ) -> ItemOutcome:
        requested = playthrough.flush_requested_through_seq
        if requested is not None and requested >= item.sequence:
            return OUTCOME_DUPLICATE
        state.playthrough = await playthrough_repo.set_flush_requested(
            self._connection, playthrough.playthrough_id, item.sequence
        )
        return OUTCOME_APPLIED

    async def _advance_watermarks(self, request: IngestRequest) -> PlaythroughRow:
        ingested_seq = await source_repo.get_contiguous_sequence(
            self._connection, PLAYTHROUGH_SCOPE, request.playthrough_id, NARRATION_KIND
        )
        latest_seq_seen = max(
            (item.sequence for item in request.items if isinstance(item, TurnItem)),
            default=NO_TURN_SEQUENCE,
        )
        row = await playthrough_repo.advance_watermarks(
            self._connection,
            request.playthrough_id,
            ingested_seq=ingested_seq,
            latest_seq_seen=latest_seq_seen,
        )
        if row is None:
            raise PlaythroughNotRegisteredError(request.playthrough_id)
        return row


def _log_request(
    row: PlaythroughRow, outcomes: list[IngestItemOutcome], started: float
) -> None:
    applied_count = sum(item.outcome == OUTCOME_APPLIED for item in outcomes)
    logger.info(
        EVENT_INGEST_APPLIED,
        playthrough_id=str(row.playthrough_id),
        item_count=len(outcomes),
        applied_count=applied_count,
        duplicate_count=len(outcomes) - applied_count,
        ingested_seq=row.ingested_seq,
        duration_ms=int((time.monotonic() - started) * MILLISECONDS_PER_SECOND),
    )


def get_ingest_service(
    connection: Annotated[AsyncConnection, Depends(get_connection)],
) -> IngestService:
    return IngestService(connection)
