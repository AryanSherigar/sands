"""ExtractionService against real Postgres and a respx-mocked model."""

import time
from collections.abc import AsyncIterator, Iterator

import pytest
import respx
import structlog
from app.integrations.extraction_queue import ExtractionQueue
from app.repositories import (
    extraction_batch_repo,
    fact_repo,
    playthrough_repo,
)
from app.services import extraction_apply, extraction_service
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.services.extraction_helpers import (
    EMPTY_OUTPUT,
    TEST_API_KEY,
    TRUNCATE_QUEUE,
    build_service,
    extraction_error,
    extraction_ok,
    ingest_more_turns,
    ingest_playthrough,
    label_of,
    make_settings,
    mock_extraction,
)

DEADLINE_SECONDS = 60
TURNS = 5


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


def _deadline() -> float:
    return time.monotonic() + DEADLINE_SECONDS


async def _output_with_fact(
    connection: AsyncConnection, playthrough_id: object, mira: object
) -> dict[str, object]:
    label = await label_of(connection, playthrough_id, 1)  # type: ignore[arg-type]
    return {
        **EMPTY_OUTPUT,
        "new_entities": [
            {
                "temp_key": "t1",
                "entity_type": "character",
                "name": "Old Marta",
                "aliases": [],
                "evidence": [label],
            }
        ],
        "facts": [
            {
                "subject": "t1",
                "predicate": "serves",
                "object": str(mira),
                "object_literal": None,
                "assertion": "occurred",
                "speaker": None,
                "evidence": [label],
            }
        ],
    }


async def _batches(pool: AsyncConnectionPool, playthrough_id: object):
    async with pool.connection() as connection:
        return await extraction_batch_repo.list_batches(
            connection,
            "playthrough",
            playthrough_id,
            None,  # type: ignore[arg-type]
        )


async def _watermark(pool: AsyncConnectionPool, playthrough_id: object) -> int:
    async with pool.connection() as connection:
        row = await playthrough_repo.get_playthrough(connection, playthrough_id)  # type: ignore[arg-type]
    assert row is not None
    return row.extracted_seq


async def test_five_turns_are_extracted_once_and_applied(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    output = await _output_with_fact(
        db_connection, playthrough.playthrough_id, playthrough.world.mira_entity_id
    )
    route = mock_extraction(model_api, extraction_ok(output))
    service = build_service(retrieval_pool, make_settings(), queue)

    result = await service.process(playthrough.playthrough_id, _deadline())

    assert result.step == "completed"
    assert route.call_count == 1
    assert result.counts.playthroughs_touched == 1
    assert result.counts.batches_applied == 1
    assert result.counts.input_tokens == 100
    batch = (await _batches(retrieval_pool, playthrough.playthrough_id))[0]
    assert (batch.status, batch.from_seq, batch.to_seq) == ("applied", 1, TURNS)
    assert batch.raw_output is not None and batch.validated_plan is not None
    assert await _watermark(retrieval_pool, playthrough.playthrough_id) == TURNS
    async with retrieval_pool.connection() as connection:
        facts = await fact_repo.list_valid_facts_at(
            connection, playthrough.playthrough_id, playthrough.world.template_id, 10
        )
    assert "extracted" in {fact.authority for fact in facts}


async def test_fewer_turns_than_a_batch_do_not_extract(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS - 1)
    route = mock_extraction(model_api, extraction_ok(EMPTY_OUTPUT))
    service = build_service(retrieval_pool, make_settings(), queue)

    result = await service.process(playthrough.playthrough_id, _deadline())

    assert result.step == "idle"
    assert route.call_count == 0


async def test_flush_extracts_a_partial_batch(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, 2, flush=True)
    mock_extraction(model_api, extraction_ok(EMPTY_OUTPUT))
    service = build_service(retrieval_pool, make_settings(), queue)

    await service.process(playthrough.playthrough_id, _deadline())

    batch = (await _batches(retrieval_pool, playthrough.playthrough_id))[0]
    assert (batch.from_seq, batch.to_seq, batch.status) == (1, 2, "applied")


async def test_apply_failure_reuses_the_stored_output_without_calling_the_model_again(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    output = await _output_with_fact(
        db_connection, playthrough.playthrough_id, playthrough.world.mira_entity_id
    )
    route = mock_extraction(model_api, extraction_ok(output))
    service = build_service(retrieval_pool, make_settings(), queue)
    real_apply = extraction_apply.apply_plan
    calls = {"count": 0}

    async def flaky_apply(connection: AsyncConnection, apply_input: object) -> int:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("boom")
        return await real_apply(connection, apply_input)  # type: ignore[arg-type]

    monkeypatch.setattr(extraction_apply, "apply_plan", flaky_apply)

    first = await service.process(playthrough.playthrough_id, _deadline())
    batch_after_failure = (await _batches(retrieval_pool, playthrough.playthrough_id))[
        0
    ]
    second = await service.process(playthrough.playthrough_id, _deadline())

    assert first.counts.batches_failed == 1
    assert batch_after_failure.status == "extracted"
    assert second.counts.batches_applied == 1
    assert route.call_count == 1
    final = (await _batches(retrieval_pool, playthrough.playthrough_id))[0]
    assert final.status == "applied"


async def test_rate_limit_stops_the_step_without_counting_an_attempt(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    mock_extraction(model_api, extraction_error(429))
    service = build_service(retrieval_pool, make_settings(), queue)

    result = await service.process(playthrough.playthrough_id, _deadline())

    assert result.step == "rate_limited"
    batch = (await _batches(retrieval_pool, playthrough.playthrough_id))[0]
    assert (batch.status, batch.attempt_count) == ("pending", 0)


async def test_thinking_config_rejection_aborts_without_burning_attempts(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    mock_extraction(model_api, extraction_error(400, "thinking_config invalid"))
    service = build_service(retrieval_pool, make_settings(), queue)

    result = await service.process(playthrough.playthrough_id, _deadline())

    assert result.step == "aborted"
    assert result.errors == ["extraction_config_rejected"]
    batch = (await _batches(retrieval_pool, playthrough.playthrough_id))[0]
    assert (batch.status, batch.attempt_count) == ("pending", 0)


async def test_transient_failures_end_in_failed_and_block_later_batches(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    route = mock_extraction(model_api, extraction_error(503))
    settings = make_settings(extraction_max_attempts=1)
    service = build_service(retrieval_pool, settings, queue)

    await service.process(playthrough.playthrough_id, _deadline())
    await ingest_more_turns(db_connection, playthrough.playthrough_id, 6, 10)
    await service.process(playthrough.playthrough_id, _deadline())

    batches = await _batches(retrieval_pool, playthrough.playthrough_id)
    assert [batch.status for batch in batches] == ["failed"]
    assert route.call_count == 1


async def test_unconfigured_client_reports_unconfigured_and_claims_nothing(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    service = build_service(retrieval_pool, make_settings(), queue, is_configured=False)

    result = await service.process(playthrough.playthrough_id, _deadline())

    assert result.step == "unconfigured"
    assert await _batches(retrieval_pool, playthrough.playthrough_id) == []


async def test_heavy_validation_drops_still_apply_the_survivors_and_count_reasons(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    good = await _output_with_fact(
        db_connection, playthrough.playthrough_id, playthrough.world.mira_entity_id
    )
    label = good["facts"][0]["evidence"][0]  # type: ignore[index]
    good["facts"].append(  # type: ignore[attr-defined]
        {
            "subject": "00000000-0000-0000-0000-000000000000",
            "predicate": "hates",
            "object": None,
            "object_literal": "x",
            "assertion": "occurred",
            "speaker": None,
            "evidence": [label],
        }
    )
    mock_extraction(model_api, extraction_ok(good))
    service = build_service(retrieval_pool, make_settings(), queue)

    result = await service.process(playthrough.playthrough_id, _deadline())

    assert result.counts.items_dropped == {"unknown_id": 1}
    assert result.counts.batches_applied == 1


async def test_a_purged_playthrough_discards_the_late_plan(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    output = await _output_with_fact(
        db_connection, playthrough.playthrough_id, playthrough.world.mira_entity_id
    )
    mock_extraction(model_api, extraction_ok(output))
    service = build_service(retrieval_pool, make_settings(), queue)
    real_apply = extraction_apply.apply_batch

    async def purge_then_apply(pool: AsyncConnectionPool, batch: object, limit: int):
        async with pool.connection() as connection:
            await connection.execute(
                "DELETE FROM memory_playthrough WHERE playthrough_id = %s",
                (playthrough.playthrough_id,),
            )
        return await real_apply(pool, batch, limit)  # type: ignore[arg-type]

    from app.services import extraction_service

    monkeypatch.setattr(extraction_service, "apply_batch", purge_then_apply)

    result = await service.process(playthrough.playthrough_id, _deadline())

    assert result.counts.batches_applied == 0
    batch = (await _batches(retrieval_pool, playthrough.playthrough_id))[0]
    assert (batch.status, batch.error) == ("applied", "scope_purged")
    async with retrieval_pool.connection() as connection:
        cursor = await connection.execute(
            "SELECT count(*) FROM memory_entity WHERE provenance = 'extracted'"
        )
        assert await cursor.fetchone() == (0,)


async def test_logs_never_contain_turn_text_or_the_api_key(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    mock_extraction(model_api, extraction_error(503, "CANARY-PROVIDER"))
    service = build_service(retrieval_pool, make_settings(), queue)

    with structlog.testing.capture_logs() as logs:
        await service.process(playthrough.playthrough_id, _deadline())

    rendered = str(logs)
    for canary in ("CANARY-TURN-TEXT", TEST_API_KEY, "CANARY-PROVIDER"):
        assert canary not in rendered


async def test_a_batch_logs_its_step_timings_without_content(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    output = await _output_with_fact(
        db_connection, playthrough.playthrough_id, playthrough.world.mira_entity_id
    )
    mock_extraction(model_api, extraction_ok(output))
    service = build_service(retrieval_pool, make_settings(), queue)

    with structlog.testing.capture_logs() as logs:
        monkeypatch.setattr(extraction_service, "logger", structlog.get_logger())
        await service.process(playthrough.playthrough_id, _deadline())

    [event] = [log for log in logs if log["event"] == "extraction_batch_timed"]
    assert set(event["stage_ms"]) == {"build", "llm", "validate_store", "apply"}
    assert all(isinstance(ms, int) and ms >= 0 for ms in event["stage_ms"].values())
    assert set(event) <= {"event", "log_level", "batch_id", "scope_kind", "stage_ms"}
