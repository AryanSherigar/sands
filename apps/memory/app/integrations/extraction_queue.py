"""procrastinate adapter: per-playthrough ordering and a bounded drain inside a request."""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from uuid import UUID

import procrastinate
import structlog
from procrastinate import exceptions as procrastinate_exceptions
from psycopg_pool import AsyncConnectionPool

TASK_NAME = "extract_batch"
WORKER_POLL_SECONDS = 0.2
SHUTDOWN_GRACE_SECONDS = 5.0

BatchHandler = Callable[[UUID], Awaitable[None]]

logger = structlog.get_logger()


class ExtractionQueue:
    """One instance per process. The procrastinate App is opened once on the shared pool;
    a closed App cannot be reopened with a different pool, so tests build their own."""

    def __init__(self, worker_count: int, stalled_seconds: int) -> None:
        self._worker_count = worker_count
        self._stalled_seconds = stalled_seconds
        self._app = procrastinate.App(connector=procrastinate.PsycopgConnector())
        self._handler: BatchHandler | None = None
        self._drain_lock = asyncio.Lock()
        self._exit_stack: AsyncExitStack | None = None
        self._task = self._app.task(name=TASK_NAME)(self._run_task)

    async def _run_task(self, batch_id: str) -> None:
        if self._handler is not None:
            await self._handler(UUID(batch_id))

    async def open(self, pool: AsyncConnectionPool) -> None:
        if self._exit_stack is not None:
            return
        stack = AsyncExitStack()
        await stack.enter_async_context(self._app.open_async(pool))
        self._exit_stack = stack

    async def close(self) -> None:
        if self._exit_stack is None:
            return
        await self._exit_stack.aclose()
        self._exit_stack = None

    async def defer(self, batch_id: UUID, scope_id: UUID) -> bool:
        """False when this batch is already waiting in the queue."""
        configured = self._task.configure(
            lock=str(scope_id), queueing_lock=str(batch_id)
        )
        try:
            await configured.defer_async(batch_id=str(batch_id))
        except procrastinate_exceptions.AlreadyEnqueued:
            return False
        return True

    async def recover_stalled_jobs(self) -> int:
        """A killed worker leaves its job `doing`, which blocks that playthrough's lock."""
        stalled = await self._app.job_manager.get_stalled_jobs(
            seconds_since_heartbeat=self._stalled_seconds
        )
        for job in stalled:
            await self._app.job_manager.retry_job_by_id_async(
                job_id=job.id, retry_at=datetime.now(UTC)
            )
        return len(stalled)

    async def drain(self, handler: BatchHandler, timeout_seconds: float) -> bool:
        """Run queued jobs until none is fetchable or the timeout hits.
        Returns True when the timeout cut the drain short."""
        async with self._drain_lock:
            return await self._drain_locked(handler, timeout_seconds)

    async def _drain_locked(
        self, handler: BatchHandler, timeout_seconds: float
    ) -> bool:
        self._handler = handler
        try:
            async with asyncio.timeout(max(timeout_seconds, 0)):
                await asyncio.gather(*self._workers())
        except TimeoutError:
            logger.info("extraction_drain_deadline_reached")
            return True
        finally:
            self._handler = None
        return False

    def _workers(self) -> list[Awaitable[None]]:
        return [
            self._app.run_worker_async(
                name=f"extraction-{index}",
                wait=False,
                concurrency=1,
                install_signal_handlers=False,
                listen_notify=False,
                fetch_job_polling_interval=WORKER_POLL_SECONDS,
                shutdown_graceful_timeout=SHUTDOWN_GRACE_SECONDS,
            )
            for index in range(self._worker_count)
        ]
