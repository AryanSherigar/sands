"""ExtractionQueue against real Postgres: drain-and-exit, per-scope ordering, dedupe."""

import asyncio
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from app.integrations.extraction_queue import ExtractionQueue
from psycopg_pool import AsyncConnectionPool

WORKER_COUNT = 3
STALLED_SECONDS = 1
DRAIN_TIMEOUT_SECONDS = 20
HANDLER_SECONDS = 0.05
TRUNCATE_QUEUE = (
    "TRUNCATE procrastinate_jobs, procrastinate_events, "
    "procrastinate_periodic_defers, procrastinate_workers RESTART IDENTITY CASCADE"
)
COUNT_JOBS_BY_STATUS = (
    "SELECT status::text, count(*) FROM procrastinate_jobs GROUP BY status"
)


@pytest.fixture
async def queue_pool(
    migrated_test_database_url: str,
) -> AsyncIterator[AsyncConnectionPool]:
    pool = AsyncConnectionPool(
        migrated_test_database_url, min_size=1, max_size=10, open=False
    )
    await pool.open()
    async with pool.connection() as connection:
        await connection.execute(TRUNCATE_QUEUE)
    yield pool
    await pool.close()


@pytest.fixture
async def queue(queue_pool: AsyncConnectionPool) -> AsyncIterator[ExtractionQueue]:
    extraction_queue = ExtractionQueue(WORKER_COUNT, STALLED_SECONDS)
    await extraction_queue.open(queue_pool)
    yield extraction_queue
    await extraction_queue.close()


async def _statuses(pool: AsyncConnectionPool) -> dict[str, int]:
    async with pool.connection() as connection:
        cursor = await connection.execute(COUNT_JOBS_BY_STATUS)
        return {row[0]: row[1] for row in await cursor.fetchall()}


class _Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, UUID]] = []
        self.running: set[UUID] = set()
        self.overlaps = 0

    def handler_for(self, scope_of: dict[UUID, UUID]):
        async def handle(batch_id: UUID) -> None:
            scope = scope_of[batch_id]
            if scope in self.running:
                self.overlaps += 1
            self.running.add(scope)
            self.events.append(("start", batch_id))
            await asyncio.sleep(HANDLER_SECONDS)
            self.events.append(("end", batch_id))
            self.running.discard(scope)

        return handle


async def test_drain_runs_every_deferred_job_then_returns(
    queue: ExtractionQueue, queue_pool: AsyncConnectionPool
) -> None:
    scope_of = {uuid4(): uuid4() for _ in range(5)}
    for batch_id, scope_id in scope_of.items():
        assert await queue.defer(batch_id, scope_id) is True
    recorder = _Recorder()

    is_cut_short = await queue.drain(
        recorder.handler_for(scope_of), DRAIN_TIMEOUT_SECONDS
    )

    assert is_cut_short is False
    assert {batch for kind, batch in recorder.events if kind == "end"} == set(scope_of)
    assert await _statuses(queue_pool) == {"succeeded": 5}


async def test_jobs_for_one_playthrough_never_overlap_and_keep_order(
    queue: ExtractionQueue,
) -> None:
    scope_id = uuid4()
    batch_ids = [uuid4() for _ in range(4)]
    scope_of = dict.fromkeys(batch_ids, scope_id)
    for batch_id in batch_ids:
        await queue.defer(batch_id, scope_id)
    recorder = _Recorder()

    await queue.drain(recorder.handler_for(scope_of), DRAIN_TIMEOUT_SECONDS)

    assert recorder.overlaps == 0
    assert [batch for kind, batch in recorder.events if kind == "start"] == batch_ids


async def test_deferring_the_same_batch_twice_is_deduplicated(
    queue: ExtractionQueue,
) -> None:
    batch_id, scope_id = uuid4(), uuid4()

    first = await queue.defer(batch_id, scope_id)
    second = await queue.defer(batch_id, scope_id)

    assert (first, second) == (True, False)


async def test_drain_with_an_empty_queue_returns_immediately(
    queue: ExtractionQueue,
) -> None:
    recorder = _Recorder()

    is_cut_short = await queue.drain(recorder.handler_for({}), DRAIN_TIMEOUT_SECONDS)

    assert is_cut_short is False
    assert recorder.events == []


async def test_drain_timeout_cuts_the_drain_short(queue: ExtractionQueue) -> None:
    scope_of = {uuid4(): uuid4() for _ in range(3)}
    for batch_id, scope_id in scope_of.items():
        await queue.defer(batch_id, scope_id)

    async def slow(_: UUID) -> None:
        await asyncio.sleep(10)

    is_cut_short = await queue.drain(slow, 0.5)

    assert is_cut_short is True


async def test_recover_stalled_jobs_with_nothing_stalled_returns_zero(
    queue: ExtractionQueue,
) -> None:
    assert await queue.recover_stalled_jobs() == 0
