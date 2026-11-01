"""POST /v1/playthroughs/{id}/memory/retry over ASGI with the real service and database."""

import time
from collections.abc import AsyncIterator, Iterator
from uuid import uuid4

import pytest
import respx
from app.integrations.extraction_queue import ExtractionQueue
from app.main import create_app
from app.repositories import embedding_failure_repo, extraction_batch_repo
from app.services.indexing_service import IndexingService
from app.services.memory_retry_service import (
    MemoryRetryService,
    get_memory_retry_service,
)
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.services.extraction_helpers import (
    EMPTY_OUTPUT,
    TRUNCATE_QUEUE,
    build_service,
    extraction_error,
    extraction_ok,
    ingest_playthrough,
    make_settings,
    mock_extraction,
)

TURNS = 5
STATUS_OK = 200
STATUS_CONFLICT = 409


@pytest.fixture
async def retrieval_pool(
    migrated_test_database_url: str, db_connection: AsyncConnection
) -> AsyncIterator[AsyncConnectionPool]:
    """Depends on db_connection so the tables are emptied before the pool is used."""
    pool = AsyncConnectionPool(migrated_test_database_url, max_size=8, open=False)
    await pool.open()
    yield pool
    await pool.close()


@pytest.fixture
async def queue(retrieval_pool: AsyncConnectionPool) -> AsyncIterator[ExtractionQueue]:
    async with retrieval_pool.connection() as connection:
        await connection.execute(TRUNCATE_QUEUE)
    extraction_queue = ExtractionQueue(2, 1)
    await extraction_queue.open(retrieval_pool)
    yield extraction_queue
    await extraction_queue.close()


@pytest.fixture
def model_api() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        yield router


def _http_client(pool: AsyncConnectionPool, queue: ExtractionQueue) -> AsyncClient:
    settings = make_settings(extraction_max_attempts=1)
    extraction = build_service(pool, settings, queue)
    indexing = IndexingService(pool, settings, None, extraction)
    app = create_app()
    app.dependency_overrides[get_memory_retry_service] = lambda: MemoryRetryService(
        pool, settings, indexing
    )
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def test_retry_resets_a_failed_batch_and_reprocesses_it(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    mock_extraction(model_api, extraction_error(503), extraction_ok(EMPTY_OUTPUT))
    settings = make_settings(extraction_max_attempts=1)
    await build_service(retrieval_pool, settings, queue).process(
        playthrough.playthrough_id, time.monotonic() + 30
    )
    async with retrieval_pool.connection() as connection:
        assert await extraction_batch_repo.has_failed_batch(
            connection, "playthrough", playthrough.playthrough_id
        )

    async with _http_client(retrieval_pool, queue) as http:
        response = await http.post(
            f"/v1/playthroughs/{playthrough.playthrough_id}/memory/retry"
        )

    body = response.json()
    assert response.status_code == STATUS_OK
    assert body["batches_reset"] == 1
    assert body["process_pending"]["extraction_counts"]["batches_applied"] == 1
    assert "extraction_failed" not in body["degraded_reasons"]
    async with retrieval_pool.connection() as connection:
        assert not await extraction_batch_repo.has_failed_batch(
            connection, "playthrough", playthrough.playthrough_id
        )


async def test_retry_clears_skipped_embedding_failures_for_the_playthrough(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
) -> None:
    playthrough = await ingest_playthrough(db_connection, 1)
    cursor = await db_connection.execute(
        "SELECT span_id FROM memory_span WHERE scope_id = %s LIMIT 1",
        (playthrough.playthrough_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    await embedding_failure_repo.record_failures(
        db_connection, "span", [row[0]], "m", "1", "embedding_permanent"
    )
    await db_connection.commit()

    async with _http_client(retrieval_pool, queue) as http:
        response = await http.post(
            f"/v1/playthroughs/{playthrough.playthrough_id}/memory/retry"
        )

    assert response.json()["failures_reset"] == 1


async def test_retry_for_an_unregistered_playthrough_is_a_409(
    retrieval_pool: AsyncConnectionPool, queue: ExtractionQueue
) -> None:
    async with _http_client(retrieval_pool, queue) as http:
        response = await http.post(f"/v1/playthroughs/{uuid4()}/memory/retry")

    assert response.status_code == STATUS_CONFLICT
    assert response.json()["code"] == "not_registered"
