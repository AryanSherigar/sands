"""POST /v1/jobs/process-pending over ASGI with the real service on the test database."""

from collections.abc import AsyncIterator

import pytest
from app.main import create_app
from app.services.indexing_service import IndexingService, get_indexing_service
from httpx import ASGITransport, AsyncClient, Response
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.services.indexing_helpers import (
    FakeEmbedder,
    add_fact,
    add_span,
    make_settings,
    make_world,
    read_indexed_seq,
    set_ingested_seq,
)

JOBS_URL = "/v1/jobs/process-pending"
STATUS_OK = 200
STATUS_UNPROCESSABLE = 422


@pytest.fixture
async def pool(
    migrated_test_database_url: str,
) -> AsyncIterator[AsyncConnectionPool]:
    """An open async pool on the migrated test database."""
    pool = AsyncConnectionPool(migrated_test_database_url, max_size=5)
    try:
        await pool.open()
        yield pool
    finally:
        await pool.close()


@pytest.fixture
async def client(
    db_connection: AsyncConnection, pool: AsyncConnectionPool
) -> AsyncIterator[AsyncClient]:
    app = create_app()
    embedder = FakeEmbedder()
    app.dependency_overrides[get_indexing_service] = lambda: IndexingService(
        pool, make_settings(), embedder
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http
    app.dependency_overrides.clear()


async def _post(client: AsyncClient, body: str | None = None) -> Response:
    kwargs = {"url": f"{JOBS_URL}"}
    if body is not None:
        kwargs["content"] = body
        kwargs["headers"] = {"content-type": "application/json"}
    return await client.post(**kwargs)


async def test_no_body_no_embedder_returns_200_unconfigured(
    db_connection: AsyncConnection, pool: AsyncConnectionPool
) -> None:
    app = create_app()
    app.dependency_overrides[get_indexing_service] = lambda: IndexingService(
        pool, make_settings(), None
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        result = await http.post(JOBS_URL)
    app.dependency_overrides.clear()

    assert result.status_code == STATUS_OK
    assert result.json()["embedding_step"] == "unconfigured"
    assert result.json()["counts"]["spans_embedded"] == 0


async def test_fake_embedder_with_data_returns_200_with_counts(
    client: AsyncClient, db_connection: AsyncConnection
) -> None:
    world = await make_world(db_connection)
    await add_span(db_connection, "playthrough", world.playthrough_id, 1, "hello world")
    await add_fact(
        db_connection, "playthrough", world.playthrough_id, "character", "fact text"
    )
    await set_ingested_seq(db_connection, world.playthrough_id, 1)

    result = await _post(client)

    assert result.status_code == STATUS_OK
    response = result.json()
    assert response["embedding_step"] == "completed"
    assert response["counts"]["spans_embedded"] == 1
    assert response["counts"]["facts_embedded"] == 1
    assert response["counts"]["batches_sent"] >= 1
    indexed_seq = await read_indexed_seq(db_connection, world.playthrough_id)
    assert indexed_seq == 1


async def test_playthrough_id_scopes_sweep(
    client: AsyncClient, db_connection: AsyncConnection
) -> None:
    world = await make_world(db_connection)
    template_id = world.template_id
    playthrough_id = world.playthrough_id

    await add_span(
        db_connection,
        "playthrough",
        playthrough_id,
        1,
        "playthrough span",
    )
    await add_span(
        db_connection,
        "template",
        template_id,
        1,
        "template span",
    )
    await db_connection.commit()

    body = f'{{"playthrough_id": "{playthrough_id}"}}'
    result = await _post(client, body)

    assert result.status_code == STATUS_OK
    response = result.json()
    assert response["embedding_step"] == "completed"
    assert response["counts"]["spans_embedded"] == 1


async def test_deadline_seconds_zero_returns_422(client: AsyncClient) -> None:
    body = '{"deadline_seconds": 0}'
    result = await _post(client, body)

    assert result.status_code == STATUS_UNPROCESSABLE


async def test_deadline_seconds_negative_returns_422(client: AsyncClient) -> None:
    body = '{"deadline_seconds": -1}'
    result = await _post(client, body)

    assert result.status_code == STATUS_UNPROCESSABLE


async def test_bad_playthrough_id_returns_422(client: AsyncClient) -> None:
    body = '{"playthrough_id": "not-a-uuid"}'
    result = await _post(client, body)

    assert result.status_code == STATUS_UNPROCESSABLE


async def test_dev_auth_dependency_applied(pool: AsyncConnectionPool) -> None:
    app = create_app()
    app.dependency_overrides[get_indexing_service] = lambda: IndexingService(
        pool, make_settings(), FakeEmbedder()
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        result = await http.post(
            JOBS_URL, headers={"x-dev-service-name": "test-caller"}
        )
    app.dependency_overrides.clear()

    assert result.status_code == STATUS_OK
