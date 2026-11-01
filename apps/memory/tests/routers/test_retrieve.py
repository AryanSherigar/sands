"""POST /v1/retrieve over ASGI with the real service on the test database and a
deterministic fake query embedder."""

import json
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest
import structlog
from app.exceptions.indexing_exceptions import EmbeddingTransientError
from app.main import create_app
from app.middleware.service_auth import verify_service_identity
from app.models.retrieve import MemoryItem, RetrieveResponse
from app.services import retrieval_branches, retrieval_response, retrieval_vector
from app.services.packing import estimate_tokens
from app.services.retrieval_service import RetrievalService, get_retrieval_service
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient, Response
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from structlog.testing import capture_logs
from tests.repositories import helpers_retrieval as helpers
from tests.repositories.helpers_retrieval import World
from tests.services.retrieval_service_helpers import (
    FakeQueryEmbedder,
    activate_model,
    add_entity,
    add_fact,
    add_scene,
    add_span,
    make_settings,
)

RETRIEVE_URL = "/v1/retrieve"
STATUS_OK = 200
STATUS_UNAUTHORIZED = 401
STATUS_FORBIDDEN = 403
STATUS_CONFLICT = 409
STATUS_UNPROCESSABLE = 422
POOL_MAX_SIZE = 6
SEQUENCE = 30
CHARS_PER_TOKEN = 3
CANARY = "canary-prose-must-never-be-logged"
LONG_ACTION = "x" * 4001
LONG_RECENT = "x" * 12001
OVERSIZED_ID_LIST = [str(uuid4()) for _ in range(501)]
OVERSIZED_SCENE_LIST = [str(uuid4()) for _ in range(101)]
OVERSIZED_NAMES = {str(uuid4()): "n" for _ in range(51)}
OVERLONG_NAME = {str(uuid4()): "n" * 101}
LIMIT_VIOLATIONS = {
    "action_text_too_long": {"action_text": LONG_ACTION},
    "recent_text_too_long": {"recent_text": LONG_RECENT},
    "last_actor_utterance_too_long": {"last_actor_utterance": LONG_ACTION},
    "revealed_ids_too_many": {"revealed_fact_ids": OVERSIZED_ID_LIST},
    "conditional_ids_too_many": {"active_conditional_fact_ids": OVERSIZED_ID_LIST},
    "scene_ids_too_many": {"scene_authored_entity_ids": OVERSIZED_SCENE_LIST},
    "participant_names_too_many": {"participant_names": OVERSIZED_NAMES},
    "participant_name_too_long": {"participant_names": OVERLONG_NAME},
    "budget_below_minimum": {"recall_budget_tokens": 199},
    "budget_above_maximum": {"recall_budget_tokens": 4001},
    "unknown_field": {"unexpected": True},
    "bad_action_mode": {"action_mode": "shout"},
    "negative_sequence": {"sequence": -1},
    "negative_window": {"recent_window_turns": -1},
}


@pytest.fixture
async def pool(
    migrated_test_database_url: str, db_connection: AsyncConnection
) -> AsyncIterator[AsyncConnectionPool]:
    """Depends on db_connection so the tables are emptied before the pool is used."""
    connection_pool = AsyncConnectionPool(
        migrated_test_database_url, min_size=1, max_size=POOL_MAX_SIZE, open=False
    )
    await connection_pool.open()
    yield connection_pool
    await connection_pool.close()


@pytest.fixture
async def world(db_connection: AsyncConnection) -> World:
    built = await helpers.build_world(db_connection)
    await activate_model(db_connection)
    await db_connection.commit()
    return built


@pytest.fixture
def embedder() -> FakeQueryEmbedder:
    return FakeQueryEmbedder()


@asynccontextmanager
async def open_client(
    pool: AsyncConnectionPool,
    embedder: FakeQueryEmbedder,
    dependency_overrides: dict[Callable[..., object], Callable[..., object]]
    | None = None,
    **settings_overrides: int | float | str,
) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides.update(dependency_overrides or {})
    settings = make_settings(**settings_overrides)
    app.dependency_overrides[get_retrieval_service] = lambda: RetrievalService(
        pool, settings, embedder
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http
    app.dependency_overrides.clear()


@pytest.fixture
async def client(
    pool: AsyncConnectionPool, embedder: FakeQueryEmbedder
) -> AsyncIterator[AsyncClient]:
    async with open_client(pool, embedder) as http:
        yield http


@pytest.fixture
def captured_logs(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, object]]]:
    with capture_logs() as entries:
        for module in (retrieval_branches, retrieval_response, retrieval_vector):
            monkeypatch.setattr(module, "logger", structlog.get_logger())
        yield entries


def build_payload(
    playthrough_id: UUID, action_text: str = "Mara", **overrides: object
) -> dict[str, object]:
    payload: dict[str, object] = {
        "playthrough_id": str(playthrough_id),
        "sequence": SEQUENCE,
        "action_text": action_text,
        "action_mode": "do",
        "actor_participant_id": str(uuid4()),
        "recent_text": "",
    }
    payload.update(overrides)
    return payload


async def post_retrieve(client: AsyncClient, payload: dict[str, object]) -> Response:
    return await client.post(RETRIEVE_URL, json=payload)


async def seed_small_corpus(connection: AsyncConnection, world: World) -> UUID:
    """Returns the authored id of the seeded entity; commits."""
    authored = uuid4()
    mara = await add_entity(
        connection, world.template_scope, "Mara", authored_id=authored
    )
    await add_fact(
        connection,
        world.template_scope,
        mara,
        "guards",
        object_literal="the cellar",
        is_embedded=True,
    )
    await add_span(
        connection,
        world.playthrough_scope,
        "Mara guards the cellar door",
        sequence=2,
        entity_ids=[mara.entity_id],
    )
    await add_tavern_scene(connection, world, mara.entity_id)
    await connection.commit()
    return authored


async def add_tavern_scene(
    connection: AsyncConnection, world: World, present_entity_id: UUID
) -> None:
    tavern = await add_entity(connection, world.playthrough_scope, "Tavern")
    await add_scene(
        connection,
        world.playthrough_id,
        4,
        location=tavern.entity_id,
        present=[present_entity_id],
    )


async def test_retrieve_returns_the_full_response_contract(
    client: AsyncClient, db_connection: AsyncConnection, world: World
) -> None:
    await seed_small_corpus(db_connection, world)

    result = await post_retrieve(client, build_payload(world.playthrough_id))

    assert result.status_code == STATUS_OK
    body = result.json()
    assert set(body) == set(RetrieveResponse.model_fields)
    parsed = RetrieveResponse.model_validate(body)
    assert parsed.items
    assert all(set(item) == set(MemoryItem.model_fields) for item in body["items"])
    assert all(item.branches for item in parsed.items)
    assert [entity.name for entity in parsed.active_entities] == ["Mara", "Tavern"]
    assert parsed.scene is not None
    assert set(body["watermarks"]) == {
        "ingested_seq",
        "indexed_seq",
        "extracted_seq",
        "latest_seq_seen",
    }
    assert parsed.degraded_reasons == []
    assert parsed.embedding_model == "model-a"
    assert parsed.skipped_branches == []


async def test_unknown_playthrough_returns_409_not_registered(
    client: AsyncClient, world: World
) -> None:
    result = await post_retrieve(client, build_payload(uuid4(), "Mara"))

    assert result.status_code == STATUS_CONFLICT
    assert result.json()["code"] == "not_registered"


@pytest.mark.parametrize(
    "overrides", LIMIT_VIOLATIONS.values(), ids=list(LIMIT_VIOLATIONS)
)
async def test_input_limit_violation_returns_422(
    client: AsyncClient, world: World, overrides: dict[str, object]
) -> None:
    payload = build_payload(world.playthrough_id, **overrides)

    result = await post_retrieve(client, payload)

    assert result.status_code == STATUS_UNPROCESSABLE


async def test_missing_required_field_returns_422(
    client: AsyncClient, world: World
) -> None:
    payload = build_payload(world.playthrough_id)
    del payload["action_mode"]

    result = await post_retrieve(client, payload)

    assert result.status_code == STATUS_UNPROCESSABLE


async def test_dev_service_header_is_accepted(
    client: AsyncClient, world: World
) -> None:
    result = await client.post(
        RETRIEVE_URL,
        json=build_payload(world.playthrough_id),
        headers={"x-dev-service-name": "test-caller"},
    )

    assert result.status_code == STATUS_OK


@pytest.mark.parametrize("status_code", [STATUS_UNAUTHORIZED, STATUS_FORBIDDEN])
async def test_service_identity_rejection_is_returned_before_any_retrieval(
    pool: AsyncConnectionPool,
    embedder: FakeQueryEmbedder,
    world: World,
    status_code: int,
) -> None:
    async def reject() -> str:
        raise HTTPException(status_code=status_code)

    async with open_client(pool, embedder, {verify_service_identity: reject}) as http:
        result = await post_retrieve(http, build_payload(world.playthrough_id))

    assert result.status_code == status_code
    assert embedder.texts == []


async def test_embedding_failure_returns_200_with_vector_skipped(
    pool: AsyncConnectionPool,
    embedder: FakeQueryEmbedder,
    db_connection: AsyncConnection,
    world: World,
) -> None:
    await seed_small_corpus(db_connection, world)
    embedder.error = EmbeddingTransientError()

    async with open_client(pool, embedder) as http:
        result = await post_retrieve(http, build_payload(world.playthrough_id))

    assert result.status_code == STATUS_OK
    assert result.json()["skipped_branches"] == ["vector"]
    assert result.json()["degraded_reasons"] == []


async def test_hidden_fact_named_by_the_action_waits_for_its_authored_id(
    client: AsyncClient, db_connection: AsyncConnection, world: World
) -> None:
    secret = uuid4()
    moon = await add_entity(
        db_connection, world.template_scope, "Moonstone", authored_id=uuid4()
    )
    await add_fact(
        db_connection,
        world.template_scope,
        moon,
        "is",
        object_literal="cursed",
        is_hidden=True,
        authored_fact_id=secret,
    )
    await db_connection.commit()

    before = await post_retrieve(
        client, build_payload(world.playthrough_id, "Moonstone")
    )
    after = await post_retrieve(
        client,
        build_payload(
            world.playthrough_id, "Moonstone", revealed_fact_ids=[str(secret)]
        ),
    )

    assert before.json()["items"] == []
    assert [item["text"] for item in after.json()["items"]] == ["Moonstone is cursed"]


async def test_omitted_window_uses_the_settings_default(
    pool: AsyncConnectionPool,
    embedder: FakeQueryEmbedder,
    db_connection: AsyncConnection,
    world: World,
) -> None:
    mara = await add_entity(db_connection, world.playthrough_scope, "Mara")
    await add_span(
        db_connection,
        world.playthrough_scope,
        "Mara waits by the door",
        sequence=28,
        entity_ids=[mara.entity_id],
    )
    await db_connection.commit()
    payload = build_payload(world.playthrough_id)
    explicit = build_payload(world.playthrough_id, "Mara", recent_window_turns=6)

    async with open_client(pool, embedder, recent_window_turns=1) as http:
        by_default = await post_retrieve(http, payload)
        by_request = await post_retrieve(http, explicit)

    assert len(by_default.json()["items"]) == 1
    assert by_request.json()["items"] == []


async def add_padding_spans(connection: AsyncConnection, world: World) -> None:
    mara = await add_entity(connection, world.playthrough_scope, "Mara")
    for number in range(20):
        await add_span(
            connection,
            world.playthrough_scope,
            f"Mara line {number} " + "x" * 90,
            sequence=1,
            entity_ids=[mara.entity_id],
            is_embedded=False,
        )
    await connection.commit()


async def test_omitted_budget_uses_the_settings_default(
    pool: AsyncConnectionPool,
    embedder: FakeQueryEmbedder,
    db_connection: AsyncConnection,
    world: World,
) -> None:
    await add_padding_spans(db_connection, world)

    async with open_client(pool, embedder, recall_budget_tokens=250) as http:
        by_default = await post_retrieve(http, build_payload(world.playthrough_id))
        by_request = await post_retrieve(
            http,
            build_payload(world.playthrough_id, "Mara", recall_budget_tokens=500),
        )

    def used(result: Response) -> int:
        return sum(
            estimate_tokens(item["text"], CHARS_PER_TOKEN)
            for item in result.json()["items"]
        )

    assert 0 < used(by_default) <= 250
    assert 250 < used(by_request) <= 500


async def add_canary_corpus(connection: AsyncConnection, world: World) -> None:
    mara = await add_entity(connection, world.playthrough_scope, f"Mara {CANARY}")
    await add_fact(
        connection,
        world.playthrough_scope,
        mara,
        "says",
        object_literal=f"{CANARY} fact",
        is_embedded=True,
    )
    await add_span(
        connection,
        world.playthrough_scope,
        f"{CANARY} span",
        sequence=2,
        entity_ids=[mara.entity_id],
    )
    await connection.commit()


async def test_no_request_or_retrieved_text_reaches_the_logs(
    client: AsyncClient,
    db_connection: AsyncConnection,
    world: World,
    captured_logs: list[dict[str, object]],
) -> None:
    await add_canary_corpus(db_connection, world)
    payload = build_payload(
        world.playthrough_id,
        f"Mara {CANARY}",
        recent_text=f"{CANARY} recent",
        last_actor_utterance=f"{CANARY} said",
        participant_names={str(uuid4()): CANARY},
    )

    result = await post_retrieve(client, payload)

    assert result.status_code == STATUS_OK
    assert result.json()["items"]
    assert CANARY not in json.dumps(captured_logs, default=str)
    assert [entry["event"] for entry in captured_logs].count("retrieve_completed") == 1
