"""retrieve() degradation: embedding and BM25 failures, model mismatch, request
ordering, transaction setup and the no-text-in-logs guarantee."""

import asyncio
import json
import time
from uuid import uuid4

import pytest
from app.exceptions.indexing_exceptions import (
    EmbeddingPermanentError,
    EmbeddingRateLimitedError,
    EmbeddingTransientError,
)
from app.exceptions.ingest_exceptions import PlaythroughNotRegisteredError
from app.repositories import span_repo
from app.services import retrieval_service
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.repositories.helpers_retrieval import World
from tests.services.retrieval_service_helpers import (
    FakeQueryEmbedder,
    add_entity,
    add_fact,
    add_span,
    build_service,
    make_request,
    texts_of,
)

OVERLAP_DELAY_SECONDS = 0.4
QUERY = "the lantern flickers in the cellar"
REQUEST_TEXT = f"Mara {QUERY}"
CANARY = "canary-prose-must-never-be-logged"


async def seed_world(connection: AsyncConnection, world: World) -> None:
    scope = world.playthrough_scope
    mara = await add_entity(connection, scope, "Mara")
    await add_fact(
        connection, scope, mara, "guards", object_literal="the cellar", is_embedded=True
    )
    await add_span(connection, scope, QUERY, sequence=2, entity_ids=[mara.entity_id])
    await connection.commit()


async def test_an_unregistered_playthrough_raises_not_registered(
    retrieval_pool: AsyncConnectionPool, retrieval_world: World
) -> None:
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    with pytest.raises(PlaythroughNotRegisteredError) as raised:
        await service.retrieve(
            make_request(retrieval_world, "Mara", playthrough_id=uuid4())
        )

    assert raised.value.status_code == 409
    assert raised.value.code == "not_registered"


@pytest.mark.parametrize(
    "error",
    [EmbeddingTransientError(), EmbeddingRateLimitedError(), EmbeddingPermanentError()],
    ids=lambda error: type(error).__name__,
)
async def test_an_embedding_error_skips_only_the_vector_branch(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
    error: Exception,
) -> None:
    await seed_world(db_connection, retrieval_world)
    embedder = FakeQueryEmbedder()
    embedder.error = error
    service = build_service(retrieval_pool, embedder)

    response = await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))

    assert response.skipped_branches == ["vector"]
    assert response.degraded_reasons == []
    assert "Mara guards the cellar" in texts_of(response.items)
    assert all("vector" not in item.branches for item in response.items)


async def test_an_embedding_timeout_skips_the_vector_branch(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    await seed_world(db_connection, retrieval_world)
    embedder = FakeQueryEmbedder()
    embedder.delay_seconds = 2.0
    service = build_service(
        retrieval_pool, embedder, retrieval_embed_timeout_seconds=0.05
    )

    response = await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))

    assert response.skipped_branches == ["vector"]
    assert response.degraded_reasons == []
    assert "Mara guards the cellar" in texts_of(response.items)


async def test_an_unconfigured_embedder_skips_the_vector_branch(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    await seed_world(db_connection, retrieval_world)
    service = build_service(retrieval_pool, None)

    response = await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))

    assert response.skipped_branches == ["vector"]
    assert response.degraded_reasons == []
    assert response.items


async def test_a_healthy_embedder_uses_the_vector_branch(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    await seed_world(db_connection, retrieval_world)
    embedder = FakeQueryEmbedder()
    service = build_service(retrieval_pool, embedder)

    response = await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))

    assert response.skipped_branches == []
    assert embedder.texts == [REQUEST_TEXT]
    assert any("vector" in item.branches for item in response.items)


async def test_the_query_is_the_action_text_plus_the_last_actor_utterance(
    retrieval_pool: AsyncConnectionPool, retrieval_world: World
) -> None:
    embedder = FakeQueryEmbedder()
    service = build_service(retrieval_pool, embedder)

    await service.retrieve(
        make_request(
            retrieval_world, "open the door", last_actor_utterance="who is there"
        )
    )

    assert embedder.texts == ["open the door who is there"]


async def test_a_blank_query_skips_bm25_and_vector_without_listing_them(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    await seed_world(db_connection, retrieval_world)
    embedder = FakeQueryEmbedder()
    service = build_service(retrieval_pool, embedder)

    response = await service.retrieve(
        make_request(retrieval_world, "  ", recent_text="Mara stands nearby")
    )

    assert embedder.texts == []
    assert response.skipped_branches == []
    assert all(item.branches == ["exact"] for item in response.items)
    assert "Mara guards the cellar" in texts_of(response.items)


async def test_a_configured_model_that_is_not_active_skips_vector(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    await seed_world(db_connection, retrieval_world)
    embedder = FakeQueryEmbedder()
    service = build_service(retrieval_pool, embedder, embedding_model_name="model-b")

    response = await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))

    assert response.skipped_branches == ["vector"]
    assert response.embedding_model == "model-a"
    assert response.degraded_reasons == []
    assert response.items


async def test_no_active_model_skips_vector_and_reports_an_empty_model_name(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    await seed_world(db_connection, retrieval_world)
    await db_connection.execute("UPDATE memory_embedding_model SET is_active = false")
    await db_connection.commit()
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    response = await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))

    assert response.skipped_branches == ["vector"]
    assert response.embedding_model == ""


async def failing_bm25(connection: AsyncConnection, *args: object) -> list:
    await connection.execute("SELECT 1 / 0")
    return []


async def test_a_bm25_database_error_skips_bm25_and_the_transaction_survives(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
    monkeypatch: pytest.MonkeyPatch,
    captured_logs: list[dict[str, object]],
) -> None:
    await seed_world(db_connection, retrieval_world)
    monkeypatch.setattr(span_repo, "search_eligible_spans_bm25", failing_bm25)
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    response = await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))

    assert response.skipped_branches == ["bm25"]
    assert "Mara guards the cellar" in texts_of(response.items)
    vector_items = [i for i in response.items if "vector" in i.branches]
    assert vector_items
    assert response.degraded_reasons == []
    failures = [e for e in captured_logs if e["event"] == "retrieval_branch_failed"]
    assert len(failures) == 1
    assert failures[0]["log_level"] == "error"
    assert failures[0]["branch"] == "bm25"
    assert failures[0]["error_class"] == "DivisionByZero"
    assert QUERY not in json.dumps(captured_logs, default=str)


async def test_the_embed_task_starts_before_the_first_database_branch(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await seed_world(db_connection, retrieval_world)
    events: list[str] = []
    for name in ("resolve_seeds", "run_exact_branch", "run_graph_branch"):
        original = getattr(retrieval_service, name)

        async def spy(
            *args: object, _name: str = name, _original=original, **kw: object
        ):
            events.append(f"db:{_name}")
            return await _original(*args, **kw)

        monkeypatch.setattr(retrieval_service, name, spy)
    service = build_service(retrieval_pool, FakeQueryEmbedder(events))

    await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))

    assert events[0] == "embed_started"
    assert events.index("embed_started") < events.index("db:resolve_seeds")
    assert events[1:4] == [
        "db:resolve_seeds",
        "db:run_exact_branch",
        "db:run_graph_branch",
    ]


async def test_the_embedding_overlaps_the_database_work(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await seed_world(db_connection, retrieval_world)
    original = retrieval_service.run_exact_branch

    async def slow_exact(*args: object, **kwargs: object):
        await asyncio.sleep(OVERLAP_DELAY_SECONDS)
        return await original(*args, **kwargs)

    monkeypatch.setattr(retrieval_service, "run_exact_branch", slow_exact)
    embedder = FakeQueryEmbedder()
    embedder.delay_seconds = OVERLAP_DELAY_SECONDS
    service = build_service(
        retrieval_pool, embedder, retrieval_embed_timeout_seconds=2.0
    )

    started = time.perf_counter()
    response = await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))
    elapsed = time.perf_counter() - started

    assert response.skipped_branches == []
    assert elapsed < OVERLAP_DELAY_SECONDS * 1.7


class CountingPool:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool
        self.acquisitions = 0

    def connection(self):
        self.acquisitions += 1
        return self._pool.connection()


async def test_one_pooled_read_only_repeatable_read_transaction_per_request(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await seed_world(db_connection, retrieval_world)
    observed: dict[str, str] = {}
    original = retrieval_service.run_exact_branch

    async def spy(connection: AsyncConnection, *args: object, **kwargs: object):
        cursor = await connection.execute(
            "SELECT current_setting('transaction_isolation'), "
            "current_setting('transaction_read_only')"
        )
        observed["isolation"], observed["read_only"] = await cursor.fetchone()
        return await original(connection, *args, **kwargs)

    monkeypatch.setattr(retrieval_service, "run_exact_branch", spy)
    pool = CountingPool(retrieval_pool)
    service = retrieval_service.RetrievalService(
        pool, build_service(retrieval_pool, None)._settings, FakeQueryEmbedder()
    )

    await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))

    assert pool.acquisitions == 1
    assert observed == {"isolation": "repeatable read", "read_only": "on"}


async def test_no_span_fact_or_query_text_reaches_the_logs(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
    captured_logs: list[dict[str, object]],
) -> None:
    world = retrieval_world
    scope = world.playthrough_scope
    mara = await add_entity(db_connection, scope, f"Mara {CANARY}")
    await add_fact(
        db_connection,
        scope,
        mara,
        "says",
        object_literal=f"{CANARY} fact",
        is_embedded=True,
    )
    await add_span(
        db_connection, scope, f"{CANARY} span", sequence=2, entity_ids=[mara.entity_id]
    )
    await db_connection.commit()
    actor = uuid4()
    request = make_request(
        world,
        f"Mara {CANARY}",
        recent_text=f"{CANARY} recent",
        last_actor_utterance=f"{CANARY} said",
        actor_participant_id=actor,
    )

    response = await build_service(retrieval_pool, FakeQueryEmbedder()).retrieve(
        request
    )

    assert response.items
    assert CANARY not in json.dumps(captured_logs, default=str)
    completed = [e for e in captured_logs if e["event"] == "retrieve_completed"]
    assert len(completed) == 1
    entry = completed[0]
    assert entry["playthrough_id"] == str(world.playthrough_id)
    assert entry["at_seq"] == 30
    assert entry["action_mode"] == "do"
    assert entry["actor_participant_id"] == str(actor)
    assert entry["packed_item_count"] == len(response.items)
    assert set(entry["stage_ms"]) >= {
        "seeds",
        "exact",
        "bm25",
        "graph",
        "vector",
        "pack",
    }
    assert entry["skipped_branches"] == []


async def test_a_second_playthrough_query_reads_its_own_scope_after_the_first(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    """Pooled connections are reused; no state of one request may reach the next."""
    world = retrieval_world
    for scope in (world.playthrough_scope, world.sibling_scope):
        mara = await add_entity(db_connection, scope, "Mara")
        await add_fact(
            db_connection, scope, mara, "is", object_literal=scope[1].hex[:6]
        )
    await db_connection.commit()
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    own = await service.retrieve(make_request(world, "Mara"))
    sibling = await service.retrieve(
        make_request(world, "Mara", playthrough_id=world.sibling_playthrough_id)
    )

    assert texts_of(own.items) == [f"Mara is {world.playthrough_id.hex[:6]}"]
    assert texts_of(sibling.items) == [
        f"Mara is {world.sibling_playthrough_id.hex[:6]}"
    ]


async def test_a_failing_database_branch_cancels_the_embedding_and_propagates(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def broken_exact(*args: object, **kwargs: object) -> list:
        raise RuntimeError("exact branch exploded")

    monkeypatch.setattr(retrieval_service, "run_exact_branch", broken_exact)
    embedder = FakeQueryEmbedder()
    embedder.delay_seconds = 5.0
    service = build_service(
        retrieval_pool, embedder, retrieval_embed_timeout_seconds=10.0
    )

    with pytest.raises(RuntimeError, match="exact branch exploded"):
        await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))

    assert embedder.was_cancelled is True


async def test_a_mismatched_model_cancels_the_started_embedding(
    retrieval_pool: AsyncConnectionPool, retrieval_world: World
) -> None:
    embedder = FakeQueryEmbedder()
    embedder.delay_seconds = 5.0
    service = build_service(
        retrieval_pool,
        embedder,
        embedding_model_name="model-b",
        retrieval_embed_timeout_seconds=10.0,
    )

    response = await service.retrieve(make_request(retrieval_world, REQUEST_TEXT))

    assert response.skipped_branches == ["vector"]
    assert embedder.was_cancelled is True
