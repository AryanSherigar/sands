""" "Retry memory": reset what failed for one playthrough, then one bounded pass."""

from uuid import UUID

import structlog
from app.config import Settings, get_settings
from app.db.pool import get_pool
from app.exceptions.ingest_exceptions import PlaythroughNotRegisteredError
from app.models.process_pending import ProcessPendingRequest
from app.models.retrieve import DegradedReason
from app.models.retry import RetryMemoryResponse
from app.repositories import (
    embedding_failure_repo,
    extraction_batch_repo,
    playthrough_repo,
)
from app.services.degraded_service import compute_degraded_reasons
from app.services.indexing_service import IndexingService, get_indexing_service
from psycopg_pool import AsyncConnectionPool

EVENT_MEMORY_RETRY = "memory_retry"

logger = structlog.get_logger()


class MemoryRetryService:
    def __init__(
        self,
        pool: AsyncConnectionPool,
        settings: Settings,
        indexing: IndexingService,
    ) -> None:
        self._pool = pool
        self._settings = settings
        self._indexing = indexing

    async def retry(self, playthrough_id: UUID) -> RetryMemoryResponse:
        """Never replays a turn and never raises for provider failures."""
        batches_reset, failures_reset = await self._reset(playthrough_id)
        process_pending = await self._indexing.process_pending(
            ProcessPendingRequest(
                playthrough_id=playthrough_id,
                deadline_seconds=self._settings.memory_retry_deadline_seconds,
            )
        )
        reasons = await self._current_reasons(playthrough_id)
        logger.info(
            EVENT_MEMORY_RETRY,
            playthrough_id=str(playthrough_id),
            batches_reset=batches_reset,
            failures_reset=failures_reset,
            degraded_reasons=reasons,
        )
        return RetryMemoryResponse(
            batches_reset=batches_reset,
            failures_reset=failures_reset,
            process_pending=process_pending,
            degraded_reasons=reasons,
        )

    async def _reset(self, playthrough_id: UUID) -> tuple[int, int]:
        async with self._pool.connection() as connection:
            playthrough = await playthrough_repo.get_playthrough(
                connection, playthrough_id
            )
            if playthrough is None:
                raise PlaythroughNotRegisteredError(playthrough_id)
            batches = await extraction_batch_repo.reset_failed_batches(
                connection, "playthrough", playthrough_id
            )
            failures = await embedding_failure_repo.reset_playthrough_failures(
                connection, playthrough_id
            )
        return len(batches), failures

    async def _current_reasons(self, playthrough_id: UUID) -> list[DegradedReason]:
        async with self._pool.connection() as connection:
            playthrough = await playthrough_repo.get_playthrough(
                connection, playthrough_id
            )
            if playthrough is None:
                return []
            return list(
                await compute_degraded_reasons(
                    connection,
                    playthrough,
                    recent_window_turns=self._settings.recent_window_turns,
                )
            )


def get_memory_retry_service() -> MemoryRetryService:
    return MemoryRetryService(get_pool(), get_settings(), get_indexing_service())
