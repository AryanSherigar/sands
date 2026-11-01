"""Delivers memory_outbox rows to the memory service, in order, per playthrough."""

import asyncio
import uuid
from dataclasses import dataclass

import structlog
from app.config import settings
from app.db.connection import AsyncSessionFactory
from app.db.models.memory_relay_claim import MemoryRelayClaim
from app.exceptions.memory_exceptions import (
    CODE_INVALID_PAYLOAD,
    CODE_NOT_REGISTERED,
    InvalidOutboxPayloadError,
    MemoryIngestError,
)
from app.integrations import memory_client
from app.models.memory_ingest import IngestRequest
from app.models.memory_relay import RelaySummary
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.memory_relay_claim_repo import MemoryRelayClaimRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.services.memory_relay_payloads import RelayBatch, build_relay_batch
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger()

EVENT_MEMORY_RELAY_DELIVERED = "memory_relay_delivered"
EVENT_MEMORY_RELAY_FAILED = "memory_relay_failed"
EVENT_MEMORY_RELAY_ORPHANED = "memory_relay_orphaned"
EVENT_MEMORY_DELIVERY_TIMED_OUT = "memory_delivery_timed_out"
EVENT_MEMORY_DELIVERY_FAILED = "memory_delivery_failed"
NO_UPSTREAM_STATUS = 0


def _error_label(error: MemoryIngestError) -> str:
    return f"{error.upstream_status or NO_UPSTREAM_STATUS}:{error.code}"


@dataclass(frozen=True)
class _ClaimedBatch:
    request: IngestRequest
    ownership_token: uuid.UUID
    row_ids: list[int]


class MemoryRelayService:
    """Deliver immutable batches under expiring ownership, without HTTP-spanning locks."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def deliver_playthrough(self, playthrough_id: uuid.UUID) -> RelaySummary:
        """Deliver the oldest batch; an active owner prevents advancing the prefix."""
        claimed, summary = await self._claim_batch(playthrough_id)
        if claimed is None:
            return summary
        error = await _ingest(claimed.request)
        finalized = await self._finalize_batch(claimed, error)
        return summary.plus(finalized)

    async def _claim_batch(
        self, playthrough_id: uuid.UUID
    ) -> tuple[_ClaimedBatch | None, RelaySummary]:
        lease_seconds = (
            settings.memory_relay_request_timeout_seconds
            + settings.memory_relay_lease_margin_seconds
        )
        async with self._session_factory() as session:
            claims = MemoryRelayClaimRepo(session)
            claim = await claims.acquire(playthrough_id, lease_seconds)
            if claim is None:
                return None, RelaySummary()
            summary = RelaySummary()
            if claim.payload is None:
                summary = await self._prepare_batch(session, claim)
            if claim.payload is None:
                await claims.remove(claim)
                await session.commit()
                return None, summary
            claimed = _ClaimedBatch(
                IngestRequest.model_validate(claim.payload),
                claim.ownership_token,
                list(claim.outbox_ids),
            )
            await session.commit()
        return claimed, summary

    async def _prepare_batch(
        self, session: AsyncSession, claim: MemoryRelayClaim
    ) -> RelaySummary:
        outbox = MemoryOutboxRepo(session)
        rows = await outbox.lock_deliverable_prefix(
            claim.playthrough_id, settings.memory_relay_batch_limit
        )
        if not rows:
            return RelaySummary()
        turn_ids = [row.turn_id for row in rows if row.turn_id is not None]
        turn_logs = await TurnLogRepo(session).list_by_turn_ids(turn_ids)
        try:
            batch = build_relay_batch(rows, {log.turn_id: log for log in turn_logs})
        except InvalidOutboxPayloadError:
            row_ids = [row.outbox_id for row in rows]
            await outbox.record_failure(row_ids, f"0:{CODE_INVALID_PAYLOAD}")
            logger.error(
                EVENT_MEMORY_RELAY_FAILED,
                playthrough_id=str(claim.playthrough_id),
                rows=len(row_ids),
                error_code=CODE_INVALID_PAYLOAD,
            )
            return RelaySummary(playthroughs_attempted=1, rows_failed=len(row_ids))
        return await self._store_batch(outbox, claim, batch)

    async def _store_batch(
        self, outbox: MemoryOutboxRepo, claim: MemoryRelayClaim, batch: RelayBatch
    ) -> RelaySummary:
        await self._dead_letter_orphans(outbox, claim.playthrough_id, batch)
        if batch.items:
            claim.payload = IngestRequest(
                delivery_id=claim.delivery_id,
                playthrough_id=claim.playthrough_id,
                items=batch.items,
            ).model_dump(mode="json")
            claim.outbox_ids = batch.sendable_row_ids
        return RelaySummary(
            playthroughs_attempted=0 if batch.items else 1,
            rows_delivered=len(batch.orphan_rows),
        )

    async def _finalize_batch(
        self, claimed: _ClaimedBatch, error: MemoryIngestError | None
    ) -> RelaySummary:
        async with self._session_factory() as session:
            claims = MemoryRelayClaimRepo(session)
            claim = await claims.get_owned(
                claimed.request.playthrough_id, claimed.ownership_token
            )
            if claim is None:
                return RelaySummary()
            result = await self._record_result(claims, claim, claimed, error)
            await session.commit()
        return result

    async def _record_result(
        self,
        claims: MemoryRelayClaimRepo,
        claim: MemoryRelayClaim,
        claimed: _ClaimedBatch,
        error: MemoryIngestError | None,
    ) -> RelaySummary:
        outbox = MemoryOutboxRepo(claims.session)
        if error is None:
            await outbox.mark_delivered(claimed.row_ids)
            await claims.remove(claim)
            result = RelaySummary(
                playthroughs_attempted=1, rows_delivered=len(claimed.row_ids)
            )
        else:
            await outbox.record_failure(claimed.row_ids, _error_label(error))
            if error.upstream_status == 409 and error.code == CODE_NOT_REGISTERED:
                await claims.remove(claim)
            else:
                await claims.release(claim)
            _log_failure(claimed.request.playthrough_id, len(claimed.row_ids), error)
            result = RelaySummary(
                playthroughs_attempted=1, rows_failed=len(claimed.row_ids)
            )
        return result

    async def deliver_pending(self) -> RelaySummary:
        """Deliver pending playthroughs, up to the pass limit."""
        async with self._session_factory() as session:
            playthrough_ids = await MemoryOutboxRepo(
                session
            ).list_playthrough_ids_with_undelivered(
                settings.memory_relay_playthrough_limit
            )
        total = RelaySummary()
        for playthrough_id in playthrough_ids:
            total = total.plus(await self.deliver_playthrough(playthrough_id))
        return total

    async def _dead_letter_orphans(
        self,
        outbox_repo: MemoryOutboxRepo,
        playthrough_id: uuid.UUID,
        batch: RelayBatch,
    ) -> None:
        for outbox_id, reason in batch.orphan_rows:
            await outbox_repo.mark_dead_lettered([outbox_id], reason)
            logger.error(
                EVENT_MEMORY_RELAY_ORPHANED,
                playthrough_id=str(playthrough_id),
                outbox_id=outbox_id,
                reason=reason,
            )


async def _ingest(request: IngestRequest) -> MemoryIngestError | None:
    try:
        response = await memory_client.ingest_items(request)
    except MemoryIngestError as error:
        return error
    logger.info(
        EVENT_MEMORY_RELAY_DELIVERED,
        playthrough_id=str(request.playthrough_id),
        rows=len(request.items),
        ingested_seq=response.ingested_seq,
    )
    return None


def _log_failure(
    playthrough_id: uuid.UUID, row_count: int, error: MemoryIngestError
) -> None:
    logger.error(
        EVENT_MEMORY_RELAY_FAILED,
        playthrough_id=str(playthrough_id),
        rows=row_count,
        error_code=error.code,
        upstream_status=error.upstream_status,
    )


_relay_service: MemoryRelayService | None = None


def get_relay_service() -> MemoryRelayService:
    """The process-wide relay bound to the application's session factory."""
    global _relay_service
    if _relay_service is None:
        _relay_service = MemoryRelayService(AsyncSessionFactory)
    return _relay_service


async def deliver_best_effort(playthrough_id: uuid.UUID) -> None:
    """Deliver this playthrough's pending rows within the delivery cap.

    Never raises: callers (the post-commit hook and the first-turn retrieve
    retry) are on a player's critical path. Whatever is not delivered stays in
    memory_outbox and the sweep picks it up.
    """
    try:
        async with asyncio.timeout(settings.memory_delivery_timeout_seconds):
            await get_relay_service().deliver_playthrough(playthrough_id)
    except TimeoutError:
        logger.warning(
            EVENT_MEMORY_DELIVERY_TIMED_OUT, playthrough_id=str(playthrough_id)
        )
    # NOTE: Intentionally broad. No delivery failure of any kind may fail a
    # turn; the rows stay undelivered and the sweep retries them.
    except Exception as exc:  # noqa: BLE001 - logged, retried by the sweep
        logger.error(
            EVENT_MEMORY_DELIVERY_FAILED,
            playthrough_id=str(playthrough_id),
            error_type=type(exc).__name__,
        )
