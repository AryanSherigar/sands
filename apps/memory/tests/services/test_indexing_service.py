"""indexing_service against a real Postgres with an injected fake embedder."""

import asyncio
import json
from collections.abc import Iterator
from uuid import UUID

import pytest
import structlog
from app.exceptions.indexing_exceptions import (
    EmbeddingRateLimitedError,
    EmbeddingTransientError,
)
from app.models.process_pending import ProcessPendingRequest, ProcessPendingResponse
from app.repositories import embedding_failure_repo
from app.services import indexing_batch, indexing_model, indexing_service
from app.services.indexing_service import DocumentEmbedder, IndexingService
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from structlog.testing import capture_logs
from tests.services.indexing_helpers import (
    MODEL_A,
    MODEL_B,
    POISON_MARKER,
    FakeEmbedder,
    World,
    add_fact,
    add_span,
    count_embeddings,
    dimension_mismatch_error,
    make_settings,
    make_world,
    read_active_model,
    read_embedded_ids,
    read_indexed_seq,
    read_model_rows,
    set_ingested_seq,
)

CANARY = "canary-prose-must-never-be-logged"
POOL_MAX_SIZE = 12
FAILURE_LIMIT = 3
LOGGING_MODULES = (indexing_service, indexing_batch, indexing_model)


@pytest.fixture
async def pool(
    migrated_test_database_url: str, db_connection: AsyncConnection
) -> AsyncConnectionPool:
    connection_pool = AsyncConnectionPool(
        migrated_test_database_url, min_size=1, max_size=POOL_MAX_SIZE, open=False
    )
    await connection_pool.open()
    yield connection_pool
    await connection_pool.close()


@pytest.fixture
async def world(db_connection: AsyncConnection) -> World:
    return await make_world(db_connection)


@pytest.fixture
def captured_logs(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, object]]]:
    with capture_logs() as entries:
        for module in LOGGING_MODULES:
            monkeypatch.setattr(module, "logger", structlog.get_logger())
        yield entries


def build_service(
    pool: AsyncConnectionPool,
    embedder: DocumentEmbedder | None,
    model: tuple[str, str] = MODEL_A,
    **overrides: int | str,
) -> IndexingService:
    return IndexingService(pool, make_settings(model, **overrides), embedder)


async def sweep(
    service: IndexingService,
    playthrough_id: UUID | None = None,
    deadline_seconds: int | None = None,
) -> ProcessPendingResponse:
    request = ProcessPendingRequest(
        playthrough_id=playthrough_id, deadline_seconds=deadline_seconds
    )
    return await service.process_pending(request)


async def failure_count(
    connection: AsyncConnection,
    kind: str,
    target_id: UUID,
    model: tuple[str, str] = MODEL_A,
) -> int:
    counts = await embedding_failure_repo.get_failure_counts(
        connection, kind, [target_id], model[0], model[1]
    )
    return counts.get(target_id, 0)


async def test_spans_and_facts_are_both_embedded(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    span_id = await add_span(
        db_connection, "playthrough", world.playthrough_id, 1, "The gate holds."
    )
    fact_id = await add_fact(
        db_connection, "playthrough", world.playthrough_id, "Mira", "the Red Guild"
    )
    embedder = FakeEmbedder()

    response = await sweep(build_service(pool, embedder))

    assert response.embedding_step == "completed"
    assert response.counts.spans_embedded == 1
    assert response.counts.facts_embedded == 1
    assert await read_embedded_ids(db_connection) == {span_id, fact_id}
    assert sorted(embedder.texts) == ["Mira serves the Red Guild", "The gate holds."]


async def test_hidden_and_conditional_content_is_embedded(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    await add_span(db_connection, *scope, 1, "hidden span", is_hidden=True)
    await add_span(db_connection, *scope, 2, "conditional span", conditional=True)
    await add_fact(db_connection, *scope, "Hidden", "one", is_hidden=True)
    await add_fact(db_connection, *scope, "Conditional", "two", conditional=True)

    response = await sweep(build_service(pool, FakeEmbedder()))

    assert response.counts.spans_embedded == 2
    assert response.counts.facts_embedded == 2
    assert await count_embeddings(db_connection) == 4


async def test_playthrough_targets_are_claimed_before_template_targets(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    for sequence, name in enumerate(["template-one", "template-two"], start=1):
        await add_span(db_connection, "template", world.template_id, sequence, name)
    for sequence, name in enumerate(["play-one", "play-two"], start=1):
        await add_span(
            db_connection, "playthrough", world.playthrough_id, sequence, name
        )
    embedder = FakeEmbedder()
    service = build_service(
        pool,
        embedder,
        embedding_claim_size=2,
        embedding_batch_size=2,
        embedding_concurrency=1,
    )

    await sweep(service)

    assert embedder.calls == [
        ["play-one", "play-two"],
        ["template-one", "template-two"],
    ]


async def test_indexed_seq_advances_past_sequences_without_spans(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    await add_span(db_connection, *scope, 1, "first")
    await add_span(db_connection, *scope, 3, "third")
    await set_ingested_seq(db_connection, world.playthrough_id, 5)

    response = await sweep(build_service(pool, FakeEmbedder()))

    assert await read_indexed_seq(db_connection, world.playthrough_id) == 5
    assert response.counts.playthroughs_advanced == 1


async def test_indexed_seq_never_passes_ingested_seq_even_when_spans_are_embedded(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    await add_span(db_connection, *scope, 1, "first")

    response = await sweep(build_service(pool, FakeEmbedder()))

    assert response.counts.spans_embedded == 1
    assert await count_embeddings(db_connection) == 1
    assert await read_indexed_seq(db_connection, world.playthrough_id) == 0
    assert response.counts.playthroughs_advanced == 0


async def test_indexed_seq_stops_before_the_first_unembedded_sequence(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    await add_span(db_connection, *scope, 1, "first")
    await add_span(db_connection, *scope, 2, f"second {POISON_MARKER}")
    await add_span(db_connection, *scope, 3, "third")
    await set_ingested_seq(db_connection, world.playthrough_id, 4)
    service = build_service(pool, FakeEmbedder(), embedding_batch_size=1)

    response = await sweep(service)

    assert await read_indexed_seq(db_connection, world.playthrough_id) == 1
    assert response.counts.playthroughs_advanced == 1
    assert await count_embeddings(db_connection) == 2


async def test_facts_alone_never_gate_indexed_seq(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    await add_span(db_connection, *scope, 1, "first")
    fact_id = await add_fact(db_connection, *scope, POISON_MARKER, "never embeds")
    await set_ingested_seq(db_connection, world.playthrough_id, 3)
    service = build_service(pool, FakeEmbedder(), embedding_batch_size=1)

    await sweep(service)

    assert fact_id not in await read_embedded_ids(db_connection)
    assert await read_indexed_seq(db_connection, world.playthrough_id) == 3


async def test_poison_target_is_retried_then_skipped_and_watermark_passes_it(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    await add_span(db_connection, *scope, 1, "fine")
    poison_id = await add_span(db_connection, *scope, 2, f"bad {POISON_MARKER}")
    await set_ingested_seq(db_connection, world.playthrough_id, 2)
    embedder = FakeEmbedder()
    service = build_service(pool, embedder, embedding_batch_size=1)

    for attempt in range(1, FAILURE_LIMIT):
        calls_before = len(embedder.calls)
        response = await sweep(service)
        poison_calls = [
            call for call in embedder.calls[calls_before:] if POISON_MARKER in call[0]
        ]
        assert len(poison_calls) == 1
        assert response.counts.targets_skipped == 0
        assert await failure_count(db_connection, "span", poison_id) == attempt
        assert await read_indexed_seq(db_connection, world.playthrough_id) == 1

    response = await sweep(service)

    assert response.counts.targets_skipped == 1
    assert await read_indexed_seq(db_connection, world.playthrough_id) == 2
    calls_after_skip = len(embedder.calls)
    idle = await sweep(service)
    assert idle.embedding_step == "idle"
    assert len(embedder.calls) == calls_after_skip


async def test_rate_limit_stops_step_writes_nothing_and_holds_watermark(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    alpha_id = await add_span(db_connection, *scope, 1, "alpha")
    await add_span(db_connection, *scope, 2, "beta")
    await set_ingested_seq(db_connection, world.playthrough_id, 2)
    embedder = FakeEmbedder()
    embedder.raise_on_call(1, EmbeddingRateLimitedError())
    service = build_service(
        pool, embedder, embedding_batch_size=1, embedding_concurrency=1
    )

    response = await sweep(service)

    assert response.embedding_step == "rate_limited"
    assert response.errors == ["embedding_rate_limited"]
    assert len(embedder.calls) == 1
    assert await count_embeddings(db_connection) == 0
    assert await failure_count(db_connection, "span", alpha_id) == 0
    assert await read_indexed_seq(db_connection, world.playthrough_id) == 0


async def test_rate_limit_keeps_batches_written_earlier_in_the_same_claim(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    alpha_id = await add_span(db_connection, *scope, 1, "alpha")
    await add_span(db_connection, *scope, 2, "beta")
    await set_ingested_seq(db_connection, world.playthrough_id, 2)
    embedder = FakeEmbedder()
    embedder.raise_on_call(2, EmbeddingRateLimitedError())
    service = build_service(
        pool, embedder, embedding_batch_size=1, embedding_concurrency=1
    )

    response = await sweep(service)

    assert response.embedding_step == "rate_limited"
    assert await read_embedded_ids(db_connection) == {alpha_id}
    assert await read_indexed_seq(db_connection, world.playthrough_id) == 1


async def test_transient_error_stops_step_without_counting_a_failure(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    alpha_id = await add_span(db_connection, *scope, 1, "alpha")
    await set_ingested_seq(db_connection, world.playthrough_id, 1)
    embedder = FakeEmbedder()
    embedder.raise_on_call(1, EmbeddingTransientError())

    response = await sweep(build_service(pool, embedder))

    assert response.embedding_step == "rate_limited"
    assert response.errors == ["embedding_transient"]
    assert await count_embeddings(db_connection) == 0
    assert await failure_count(db_connection, "span", alpha_id) == 0
    assert await read_indexed_seq(db_connection, world.playthrough_id) == 0


async def test_dimension_mismatch_aborts_step_and_logs_at_error_level(
    pool: AsyncConnectionPool,
    db_connection: AsyncConnection,
    world: World,
    captured_logs: list[dict[str, object]],
) -> None:
    scope = ("playthrough", world.playthrough_id)
    alpha_id = await add_span(db_connection, *scope, 1, "alpha")
    await add_span(db_connection, *scope, 2, "beta")
    embedder = FakeEmbedder()
    embedder.raise_on_call(1, dimension_mismatch_error())
    service = build_service(
        pool, embedder, embedding_batch_size=1, embedding_concurrency=1
    )

    response = await sweep(service)

    assert response.embedding_step == "aborted"
    assert response.errors == ["embedding_dimension_mismatch"]
    assert len(embedder.calls) == 1
    assert await count_embeddings(db_connection) == 0
    assert await failure_count(db_connection, "span", alpha_id) == 1
    error_entries = [entry for entry in captured_logs if entry["log_level"] == "error"]
    assert [entry["event"] for entry in error_entries] == [
        "embedding_dimension_mismatch"
    ]


async def test_count_mismatch_counts_against_failures_and_writes_nothing(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    first_id = await add_span(db_connection, *scope, 1, "alpha")
    second_id = await add_span(db_connection, *scope, 2, "beta")
    embedder = FakeEmbedder()
    embedder.return_wrong_count_on_call(1)
    service = build_service(pool, embedder)

    response = await sweep(service)

    assert response.embedding_step == "completed"
    assert response.errors == ["embedding_anomaly"]
    assert await count_embeddings(db_connection) == 0
    assert await failure_count(db_connection, "span", first_id) == 1
    assert await failure_count(db_connection, "span", second_id) == 1
    retry = await sweep(service)
    assert retry.counts.spans_embedded == 2


async def test_concurrent_sweeps_embed_each_target_exactly_once(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    texts = [f"span number {index}" for index in range(40)]
    for index, text in enumerate(texts, start=1):
        await add_span(db_connection, *scope, index, text)
    embedder = FakeEmbedder(delay_seconds=0.02)
    overrides = {"embedding_claim_size": 5, "embedding_batch_size": 5}
    first = build_service(pool, embedder, embedding_concurrency=4, **overrides)
    second = build_service(pool, embedder, embedding_concurrency=4, **overrides)

    responses = await asyncio.gather(sweep(first), sweep(second))

    assert sorted(embedder.texts) == sorted(texts)
    assert await count_embeddings(db_connection) == len(texts)
    embedded_counts = [response.counts.spans_embedded for response in responses]
    assert sum(embedded_counts) == len(texts)
    assert all(count > 0 for count in embedded_counts)


async def test_deadline_stops_new_batches_and_reports_deadline_reached(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    span_total = 8
    for index in range(1, span_total + 1):
        await add_span(db_connection, *scope, index, f"slow span {index}")
    embedder = FakeEmbedder(delay_seconds=0.6)
    service = build_service(
        pool, embedder, embedding_batch_size=1, embedding_concurrency=1
    )

    response = await sweep(service, deadline_seconds=1)

    assert response.embedding_step == "deadline_reached"
    assert 1 <= len(embedder.calls) < span_total
    assert all(deadline is not None for deadline in embedder.deadlines)
    assert await count_embeddings(db_connection) == len(embedder.calls)
    finished = await sweep(service)
    assert finished.embedding_step == "completed"


async def test_scoped_sweep_skips_template_scope_and_other_playthroughs(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    other = await make_world(db_connection)
    mine_id = await add_span(
        db_connection, "playthrough", world.playthrough_id, 1, "mine"
    )
    await add_span(db_connection, "template", world.template_id, 1, "template")
    await add_span(db_connection, "playthrough", other.playthrough_id, 1, "other")
    embedder = FakeEmbedder()

    await sweep(build_service(pool, embedder), world.playthrough_id)

    assert embedder.texts == ["mine"]
    assert await read_embedded_ids(db_connection) == {mine_id}


async def test_scoped_sweep_neither_flips_the_model_nor_deletes_vectors(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    await add_span(db_connection, "playthrough", world.playthrough_id, 1, "only span")
    await sweep(build_service(pool, FakeEmbedder(), MODEL_A))
    await add_span(db_connection, "playthrough", world.playthrough_id, 2, "new span")

    response = await sweep(
        build_service(pool, FakeEmbedder(), MODEL_B), world.playthrough_id
    )

    assert response.counts.model_flipped is False
    assert response.counts.old_vectors_deleted == 0
    assert await read_active_model(db_connection) == MODEL_A
    assert await count_embeddings(db_connection, MODEL_A) == 1
    assert await count_embeddings(db_connection, MODEL_B) == 2


async def test_unconfigured_embedder_claims_nothing_and_warns(
    pool: AsyncConnectionPool,
    db_connection: AsyncConnection,
    world: World,
    captured_logs: list[dict[str, object]],
) -> None:
    await add_span(db_connection, "playthrough", world.playthrough_id, 1, "alpha")

    response = await sweep(build_service(pool, None))

    assert response.embedding_step == "unconfigured"
    assert response.counts.spans_embedded == 0
    assert await count_embeddings(db_connection) == 0
    assert await read_model_rows(db_connection) == []
    warnings = [entry for entry in captured_logs if entry["log_level"] == "warning"]
    assert [entry["event"] for entry in warnings] == ["embedding_unconfigured"]


async def test_empty_queue_reports_idle_with_zero_counts(
    pool: AsyncConnectionPool, world: World
) -> None:
    response = await sweep(build_service(pool, FakeEmbedder()))

    assert response.embedding_step == "idle"
    assert response.counts.model_dump() == {
        "spans_embedded": 0,
        "facts_embedded": 0,
        "characters_embedded": 0,
        "tokens_estimated": 0,
        "batches_sent": 0,
        "targets_skipped": 0,
        "playthroughs_advanced": 0,
        "model_flipped": False,
        "old_vectors_deleted": 0,
        "templates_gc_deleted": 0,
        "templates_gc_retained": 0,
    }
    assert response.errors == []


async def test_response_counts_characters_tokens_and_batches(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    span_texts = ["abcdef", "ghijk", "lmn"]
    for index, text in enumerate(span_texts, start=1):
        await add_span(db_connection, *scope, index, text)
    await add_fact(db_connection, *scope, "Mira", "x")
    settings = make_settings(embedding_batch_size=2)
    service = IndexingService(pool, settings, FakeEmbedder())

    response = await sweep(service)

    fact_text = "Mira serves x"
    expected_chars = sum(len(text) for text in span_texts) + len(fact_text)
    assert response.counts.characters_embedded == expected_chars
    assert (
        response.counts.tokens_estimated
        == expected_chars // settings.span_chars_per_token
    )
    assert response.counts.batches_sent == 2
    assert response.counts.spans_embedded == 3
    assert response.counts.facts_embedded == 1


async def test_first_boot_registers_and_activates_the_configured_model(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    await sweep(build_service(pool, FakeEmbedder()))

    assert await read_model_rows(db_connection) == [("model-a", "1", True)]


async def test_switched_model_is_registered_inactive_and_embedded_under_config(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    await add_span(db_connection, *scope, 1, "kept")
    await sweep(build_service(pool, FakeEmbedder(), MODEL_A))
    await add_span(db_connection, *scope, 2, f"bad {POISON_MARKER}")

    response = await sweep(
        build_service(pool, FakeEmbedder(), MODEL_B, embedding_batch_size=1)
    )

    assert await read_model_rows(db_connection) == [
        ("model-a", "1", True),
        ("model-b", "1", False),
    ]
    assert response.counts.model_flipped is False
    assert await count_embeddings(db_connection, MODEL_B) == 1


async def test_partial_coverage_does_not_flip_the_model(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    await add_span(db_connection, *scope, 1, "kept")
    await sweep(build_service(pool, FakeEmbedder(), MODEL_A))
    await add_span(db_connection, *scope, 2, f"bad {POISON_MARKER}")

    response = await sweep(
        build_service(pool, FakeEmbedder(), MODEL_B, embedding_batch_size=1)
    )

    assert response.embedding_step == "completed"
    assert response.counts.model_flipped is False
    assert await read_active_model(db_connection) == MODEL_A


async def test_full_coverage_flips_and_old_vectors_go_in_a_later_sweep(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    await add_span(db_connection, *scope, 1, "kept")
    await add_fact(db_connection, *scope, "Mira", "the Guild")
    await sweep(build_service(pool, FakeEmbedder(), MODEL_A))

    flip_sweep = await sweep(build_service(pool, FakeEmbedder(), MODEL_B))

    assert flip_sweep.counts.model_flipped is True
    assert flip_sweep.counts.old_vectors_deleted == 0
    assert await read_active_model(db_connection) == MODEL_B
    assert await count_embeddings(db_connection, MODEL_A) == 2
    later_sweep = await sweep(build_service(pool, FakeEmbedder(), MODEL_B))
    assert later_sweep.counts.old_vectors_deleted == 2
    assert later_sweep.counts.model_flipped is False
    assert await count_embeddings(db_connection, MODEL_A) == 0
    assert await count_embeddings(db_connection, MODEL_B) == 2


async def test_reverted_config_deletes_the_abandoned_models_vectors(
    pool: AsyncConnectionPool, db_connection: AsyncConnection, world: World
) -> None:
    scope = ("playthrough", world.playthrough_id)
    await add_span(db_connection, *scope, 1, "kept")
    await sweep(build_service(pool, FakeEmbedder(), MODEL_A))
    await add_span(db_connection, *scope, 2, f"bad {POISON_MARKER}")
    await sweep(build_service(pool, FakeEmbedder(), MODEL_B, embedding_batch_size=1))
    assert await count_embeddings(db_connection, MODEL_B) == 1

    reverted = await sweep(build_service(pool, FakeEmbedder(), MODEL_A))

    assert reverted.counts.old_vectors_deleted == 1
    assert await count_embeddings(db_connection, MODEL_B) == 0
    assert await count_embeddings(db_connection, MODEL_A) == 1


async def test_logs_have_one_line_per_batch_and_never_contain_prose(
    pool: AsyncConnectionPool,
    db_connection: AsyncConnection,
    world: World,
    captured_logs: list[dict[str, object]],
) -> None:
    scope = ("playthrough", world.playthrough_id)
    await add_span(db_connection, *scope, 1, f"{CANARY} one")
    await add_span(db_connection, *scope, 2, f"{CANARY} {POISON_MARKER}")
    await add_fact(db_connection, *scope, CANARY, f"{CANARY} three")
    embedder = FakeEmbedder()
    service = build_service(pool, embedder, embedding_batch_size=1)

    await sweep(service)

    batch_entries = [e for e in captured_logs if e["event"] == "embedding_batch"]
    assert len(batch_entries) == len(embedder.calls) == 3
    assert {entry["outcome"] for entry in batch_entries} == {"written", "permanent"}
    assert CANARY not in json.dumps(captured_logs, default=str)
