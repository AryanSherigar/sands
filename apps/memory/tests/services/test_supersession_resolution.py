"""Supersession resolution inside extraction: real Postgres, respx-mocked model."""

import time
from collections.abc import AsyncIterator, Iterator
from uuid import UUID

import pytest
import respx
from app.integrations.extraction_queue import ExtractionQueue
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.services.extraction_helpers import (
    EMPTY_OUTPUT,
    TRUNCATE_QUEUE,
    Playthrough,
    build_service,
    extraction_error,
    extraction_ok,
    ingest_playthrough,
    label_of,
    make_settings,
    mock_extraction,
)
from tests.services.ingest_helpers import INITIAL_RANK

DEADLINE_SECONDS = 60
TURNS = 5
SELECT_SUPERSEDED = "SELECT fact_id FROM memory_supersession WHERE playthrough_id = %s"
NEW_RANK = "sergeant"


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


async def _rank_change_output(
    connection: AsyncConnection, playthrough: Playthrough, predicate: str
) -> dict[str, object]:
    label = await label_of(connection, playthrough.playthrough_id, 1)
    fact = {
        "subject": str(playthrough.world.mira_entity_id),
        "predicate": predicate,
        "object": None,
        "object_literal": NEW_RANK,
        "assertion": "occurred",
        "speaker": None,
        "evidence": [label],
    }
    return {**EMPTY_OUTPUT, "facts": [fact]}


def _judge_output(fact_id: UUID | str, reason: str = "promoted") -> dict[str, object]:
    judgement = {
        "new_fact_index": 0,
        "superseded_fact_id": str(fact_id),
        "reason": reason,
    }
    return {"judgements": [judgement]}


async def _superseded_ids(
    pool: AsyncConnectionPool, playthrough: Playthrough
) -> set[UUID]:
    async with pool.connection() as connection:
        cursor = await connection.execute(
            SELECT_SUPERSEDED, (playthrough.playthrough_id,)
        )
        return {row[0] for row in await cursor.fetchall()}


async def _run(
    pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    playthrough: Playthrough,
    **settings: object,
):
    service = build_service(pool, make_settings(**settings), queue)
    return await service.process(
        playthrough.playthrough_id, time.monotonic() + DEADLINE_SECONDS
    )


async def test_resolution_is_off_by_default(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    output = await _rank_change_output(db_connection, playthrough, "rank")
    route = mock_extraction(model_api, extraction_ok(output))

    await _run(
        retrieval_pool,
        queue,
        playthrough,
        supersession_functional_predicates=("rank",),
    )

    assert route.call_count == 1
    assert await _superseded_ids(retrieval_pool, playthrough) == set()


async def test_a_functional_predicate_retires_the_old_fact_without_a_judge_call(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    output = await _rank_change_output(db_connection, playthrough, "rank")
    route = mock_extraction(model_api, extraction_ok(output))

    result = await _run(
        retrieval_pool,
        queue,
        playthrough,
        supersession_resolution_mode="rules",
        supersession_functional_predicates=("rank",),
    )

    assert route.call_count == 1
    assert result.counts.batches_applied == 1
    assert await _superseded_ids(retrieval_pool, playthrough) == {
        playthrough.world.rank_fact.fact_id
    }


async def test_a_non_functional_predicate_is_decided_by_the_judge(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    rank_fact_id = playthrough.world.rank_fact.fact_id
    output = await _rank_change_output(db_connection, playthrough, "rank")
    route = mock_extraction(
        model_api, extraction_ok(output), extraction_ok(_judge_output(rank_fact_id))
    )

    result = await _run(
        retrieval_pool,
        queue,
        playthrough,
        supersession_resolution_mode="rules_and_judge",
    )

    assert route.call_count == 2
    assert result.counts.input_tokens == 200
    assert await _superseded_ids(retrieval_pool, playthrough) == {rank_fact_id}
    judge_request = route.calls[1].request.content.decode()
    assert str(rank_fact_id) in judge_request
    assert INITIAL_RANK in judge_request


async def test_a_judge_failure_leaves_the_batch_applied_without_the_supersession(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    output = await _rank_change_output(db_connection, playthrough, "rank")
    mock_extraction(model_api, extraction_ok(output), extraction_error(500))

    result = await _run(
        retrieval_pool,
        queue,
        playthrough,
        supersession_resolution_mode="rules_and_judge",
    )

    assert result.counts.batches_applied == 1
    assert result.counts.items_dropped.get("judge_failed") == 1
    assert await _superseded_ids(retrieval_pool, playthrough) == set()


async def test_a_judge_cannot_retire_a_fact_it_was_not_offered(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    playthrough = await ingest_playthrough(db_connection, TURNS)
    output = await _rank_change_output(db_connection, playthrough, "rank")
    invented = playthrough.world.mira_entity_id
    mock_extraction(
        model_api, extraction_ok(output), extraction_ok(_judge_output(invented))
    )

    result = await _run(
        retrieval_pool,
        queue,
        playthrough,
        supersession_resolution_mode="rules_and_judge",
    )

    assert result.counts.items_dropped.get("judge_unoffered_id") == 1
    assert await _superseded_ids(retrieval_pool, playthrough) == set()
