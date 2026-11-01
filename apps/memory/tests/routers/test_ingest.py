"""POST /v1/ingest/items over ASGI with the real service on the test database."""

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from app.main import create_app
from app.services.ingest_service import IngestService, get_ingest_service
from httpx import ASGITransport, AsyncClient, Response
from psycopg import AsyncConnection
from tests.services.ingest_helpers import (
    TurnSpec,
    build_request,
    flush_item,
    register_item,
    seed_template_world,
    turn_item,
)

INGEST_URL = "/v1/ingest/items"
OVERSIZED_BATCH = 51


@pytest.fixture
async def client(db_connection: AsyncConnection) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_ingest_service] = lambda: IngestService(db_connection)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http
    app.dependency_overrides.clear()


async def _post(client: AsyncClient, request_body: str) -> Response:
    return await client.post(
        INGEST_URL,
        content=request_body,
        headers={"content-type": "application/json"},
    )


async def _register(
    client: AsyncClient, db_connection: AsyncConnection, playthrough_id: UUID
) -> None:
    world = await seed_template_world(db_connection)
    request = build_request(playthrough_id, register_item(world.scenario_id))
    result = await _post(client, request.model_dump_json())
    assert result.status_code == 200


async def test_ingest_register_turns_and_flush_returns_outcomes(
    client: AsyncClient, db_connection: AsyncConnection
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    request = build_request(
        playthrough_id,
        register_item(world.scenario_id),
        turn_item(TurnSpec(1, narration="The gate holds.", action="Look.")),
        turn_item(TurnSpec(2, narration="Rain falls.")),
        flush_item(2),
    )

    result = await _post(client, request.model_dump_json())

    assert result.status_code == 200
    assert result.json() == {
        "playthrough_id": str(playthrough_id),
        "ingested_seq": 2,
        "latest_seq_seen": 2,
        "items": [
            {"item_kind": "register_playthrough", "sequence": 0, "outcome": "applied"},
            {"item_kind": "turn", "sequence": 1, "outcome": "applied"},
            {"item_kind": "turn", "sequence": 2, "outcome": "applied"},
            {"item_kind": "flush", "sequence": 2, "outcome": "applied"},
        ],
    }


async def test_ingest_redelivery_reports_duplicates(
    client: AsyncClient, db_connection: AsyncConnection
) -> None:
    world = await seed_template_world(db_connection)
    request = build_request(
        uuid4(),
        register_item(world.scenario_id),
        turn_item(TurnSpec(1, narration="The gate holds.")),
    )
    await _post(client, request.model_dump_json())

    result = await _post(client, request.model_dump_json())

    assert result.status_code == 200
    outcomes = [item["outcome"] for item in result.json()["items"]]
    assert outcomes == ["duplicate", "duplicate"]


async def test_ingest_turn_before_register_returns_409_not_registered(
    client: AsyncClient,
) -> None:
    request = build_request(uuid4(), turn_item(TurnSpec(1, narration="x")))

    result = await _post(client, request.model_dump_json())

    assert result.status_code == 409
    assert result.json()["code"] == "not_registered"


async def test_ingest_same_turn_id_different_narration_returns_409_content_conflict(
    client: AsyncClient, db_connection: AsyncConnection
) -> None:
    playthrough_id = uuid4()
    await _register(client, db_connection, playthrough_id)
    original = TurnSpec(1, narration="The gate holds.")
    conflicting = TurnSpec(1, narration="The gate falls.", turn_id=original.turn_id)
    await _post(
        client, build_request(playthrough_id, turn_item(original)).model_dump_json()
    )

    result = await _post(
        client, build_request(playthrough_id, turn_item(conflicting)).model_dump_json()
    )

    assert result.status_code == 409
    assert result.json()["code"] == "content_conflict"


async def test_ingest_oversized_batch_returns_422_batch_too_large(
    client: AsyncClient,
) -> None:
    items = [turn_item(TurnSpec(seq, narration="x")) for seq in range(1, 52)]
    assert len(items) == OVERSIZED_BATCH

    result = await _post(client, build_request(uuid4(), *items).model_dump_json())

    assert result.status_code == 422
    assert result.json()["code"] == "batch_too_large"


async def test_ingest_unordered_items_returns_422_items_out_of_order(
    client: AsyncClient,
) -> None:
    request = build_request(
        uuid4(),
        turn_item(TurnSpec(2, narration="b")),
        turn_item(TurnSpec(1, narration="a")),
    )

    result = await _post(client, request.model_dump_json())

    assert result.status_code == 422
    assert result.json()["code"] == "items_out_of_order"


async def test_ingest_malformed_body_returns_422(client: AsyncClient) -> None:
    result = await _post(client, '{"playthrough_id": "not-a-uuid", "items": []}')

    assert result.status_code == 422
