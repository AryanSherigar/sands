"""POST /v1/purge and GET /v1/scopes over ASGI with the real service."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from app.main import create_app
from app.models.purge import PURGE_MAX_IDS
from app.services.purge_service import PurgeService, get_purge_service
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.services import purge_helpers as helpers

PURGE_URL = "/v1/purge"
SCOPES_URL = "/v1/scopes"
STATUS_OK = 200
STATUS_UNPROCESSABLE = 422


@pytest.fixture
async def pool(
    migrated_test_database_url: str, db_connection: AsyncConnection
) -> AsyncIterator[AsyncConnectionPool]:
    """Depends on db_connection so the tables are emptied before the pool is used."""
    pool = AsyncConnectionPool(migrated_test_database_url, max_size=5, open=False)
    await pool.open()
    yield pool
    await pool.close()


@pytest.fixture
async def client(pool: AsyncConnectionPool) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_purge_service] = lambda: PurgeService(pool)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http
    app.dependency_overrides.clear()


async def test_purge_returns_the_counts(
    db_connection: AsyncConnection, client: AsyncClient
) -> None:
    template = await helpers.build_template(db_connection)
    world = await helpers.build_playthrough(db_connection, template)
    await db_connection.commit()

    response = await client.post(
        PURGE_URL,
        json={
            "playthrough_ids": [str(world.playthrough_id)],
            "scenario_ids": [str(template.scenario_id)],
        },
    )

    assert response.status_code == STATUS_OK
    assert response.json() == {
        "playthroughs_purged": 1,
        "templates_purged": 1,
        "templates_retained_in_use": 0,
    }


async def test_purge_of_unknown_ids_is_a_noop(client: AsyncClient) -> None:
    response = await client.post(PURGE_URL, json={"playthrough_ids": [str(uuid4())]})

    assert response.status_code == STATUS_OK
    assert response.json()["playthroughs_purged"] == 0


async def test_an_empty_request_is_rejected(client: AsyncClient) -> None:
    response = await client.post(PURGE_URL, json={})

    assert response.status_code == STATUS_UNPROCESSABLE


async def test_more_than_the_maximum_ids_is_rejected(client: AsyncClient) -> None:
    ids = [str(uuid4()) for _ in range(PURGE_MAX_IDS + 1)]

    response = await client.post(PURGE_URL, json={"playthrough_ids": ids})

    assert response.status_code == STATUS_UNPROCESSABLE


async def test_the_maximum_number_of_ids_is_accepted(client: AsyncClient) -> None:
    half = PURGE_MAX_IDS // 2
    body = {
        "playthrough_ids": [str(uuid4()) for _ in range(half)],
        "scenario_ids": [str(uuid4()) for _ in range(PURGE_MAX_IDS - half)],
    }

    response = await client.post(PURGE_URL, json=body)

    assert response.status_code == STATUS_OK


async def test_scopes_lists_playthroughs_and_templates(
    db_connection: AsyncConnection, client: AsyncClient
) -> None:
    template = await helpers.build_template(db_connection, publish_revision=3)
    world = await helpers.build_playthrough(db_connection, template)
    await db_connection.commit()

    response = await client.get(SCOPES_URL)

    body = response.json()
    assert response.status_code == STATUS_OK
    assert [item["playthrough_id"] for item in body["playthroughs"]] == [
        str(world.playthrough_id)
    ]
    assert [
        (item["template_id"], item["scenario_id"], item["publish_revision"])
        for item in body["templates"]
    ] == [(str(template.template_id), str(template.scenario_id), 3)]
    assert body["playthroughs"][0]["created_at"]
    assert body["templates"][0]["created_at"]


async def test_scopes_is_empty_without_data(
    db_connection: AsyncConnection, client: AsyncClient
) -> None:
    response = await client.get(SCOPES_URL)

    assert response.json() == {"playthroughs": [], "templates": []}
