"""Newbie template enrichment: chunking, cost cap, lifecycle and scope rules."""

import time
from collections.abc import AsyncIterator, Iterator
from uuid import UUID

import pytest
import respx
from app.integrations.extraction_queue import ExtractionQueue
from app.models.evidence import SpanRow
from app.repositories import (
    entity_repo,
    extraction_batch_repo,
    fact_repo,
    template_repo,
)
from app.services.enrichment_service import chunk_spans
from app.services.template_service import TemplateService
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.services.extraction_helpers import (
    EMPTY_OUTPUT,
    TRUNCATE_QUEUE,
    build_service,
    extraction_ok,
    make_settings,
    mock_extraction,
)
from tests.services.template_helpers import build_newbie_request, story_card

DEADLINE_SECONDS = 60
LORE = "Marta keeps the lighthouse above Ashfall.\n\nThe Vigil watches the cairn."
CARDS = [
    story_card("c1", "Marta", "Character", "Old Marta tends the lighthouse."),
    story_card("c2", "Ashfall", "Location", "A burned village by the sea."),
]


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


def _span(tokens: int, label: str = "L1") -> SpanRow:
    return SpanRow(
        span_id=UUID(int=1),
        source_id=UUID(int=2),
        scope_kind="template",
        scope_id=UUID(int=3),
        sequence=0,
        ordinal=1,
        start_offset=0,
        end_offset=1,
        text="x",
        token_count=tokens,
        label=label,
    )


def _deadline() -> float:
    return time.monotonic() + DEADLINE_SECONDS


async def _newbie_template(connection: AsyncConnection, lore: str = LORE) -> UUID:
    request = build_newbie_request(CARDS, world_lore=lore)
    result = await TemplateService(connection).build_template(request)
    await connection.commit()
    return result.response.template_id


async def _template_row(pool: AsyncConnectionPool, template_id: UUID):
    async with pool.connection() as connection:
        row = await template_repo.get_template(connection, template_id)
    assert row is not None
    return row


def test_chunks_respect_the_token_budget_and_keep_order() -> None:
    spans = [_span(40, f"L{n}") for n in range(1, 6)]

    chunks = chunk_spans(spans, 100)

    assert [[span.label for span in chunk] for chunk in chunks] == [
        ["L1", "L2"],
        ["L3", "L4"],
        ["L5"],
    ]


def test_a_span_larger_than_the_budget_forms_its_own_chunk() -> None:
    chunks = chunk_spans([_span(10, "L1"), _span(500, "L2"), _span(10, "L3")], 100)

    assert [[span.label for span in chunk] for chunk in chunks] == [
        ["L1"],
        ["L2"],
        ["L3"],
    ]


def test_no_spans_yield_no_chunks() -> None:
    assert chunk_spans([], 100) == []


async def test_enrichment_adds_extracted_entities_and_facts_then_becomes_ready(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    template_id = await _newbie_template(db_connection)
    async with retrieval_pool.connection() as connection:
        marta = (
            await entity_repo.find_entities_by_alias(
                connection, [("template", template_id)], ["marta"]
            )
        )[0][1]
        spans_labels = [span.label for span in await _spans(connection, template_id)]
    output = {
        **EMPTY_OUTPUT,
        "new_entities": [
            {
                "temp_key": "t1",
                "entity_type": "location",
                "name": "The Vigil Cairn",
                "aliases": [],
                "evidence": [spans_labels[0]],
            }
        ],
        "facts": [
            {
                "subject": str(marta.entity_id),
                "predicate": "keeps",
                "object": "t1",
                "object_literal": None,
                "assertion": "occurred",
                "speaker": None,
                "evidence": [spans_labels[0]],
            }
        ],
    }
    route = mock_extraction(model_api, extraction_ok(output))
    service = build_service(retrieval_pool, make_settings(), queue)

    result = await service.process(None, _deadline())

    assert result.step == "completed"
    assert route.call_count >= 1
    assert (
        await _template_row(retrieval_pool, template_id)
    ).enrichment_status == "ready"
    async with retrieval_pool.connection() as connection:
        facts = await fact_repo.list_valid_facts_at(
            connection, UUID(int=9), template_id, 0
        )
    assert {fact.authority for fact in facts} == {"extracted"}


async def _spans(connection: AsyncConnection, template_id: UUID) -> list[SpanRow]:
    from app.repositories import span_repo

    return await span_repo.list_template_spans_in_order(connection, template_id)


async def test_chunks_become_sequential_template_batches(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    template_id = await _newbie_template(db_connection)
    mock_extraction(model_api, extraction_ok(EMPTY_OUTPUT))
    service = build_service(
        retrieval_pool, make_settings(enrichment_chunk_tokens=10), queue
    )

    result = await service.process(None, _deadline())

    async with retrieval_pool.connection() as connection:
        batches = await extraction_batch_repo.list_batches(
            connection, "template", template_id, None
        )
    assert len(batches) > 1
    assert {batch.status for batch in batches} == {"applied"}
    assert sorted(batch.from_seq for batch in batches) == list(
        range(1, len(batches) + 1)
    )
    assert result.counts.enrichment_batches == len(batches)


async def test_a_template_over_the_cap_fails_with_a_stable_code_and_makes_no_calls(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    template_id = await _newbie_template(db_connection)
    route = mock_extraction(model_api, extraction_ok(EMPTY_OUTPUT))
    service = build_service(
        retrieval_pool, make_settings(enrichment_max_input_tokens=1), queue
    )

    await service.process(None, _deadline())

    row = await _template_row(retrieval_pool, template_id)
    assert (row.enrichment_status, row.enrichment_error) == (
        "failed",
        "enrichment_over_cap",
    )
    assert route.call_count == 0


async def test_a_failed_chunk_fails_the_template_and_skips_later_chunks(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    from tests.services.extraction_helpers import extraction_error

    template_id = await _newbie_template(db_connection)
    route = mock_extraction(model_api, extraction_error(503))
    service = build_service(
        retrieval_pool,
        make_settings(enrichment_chunk_tokens=10, extraction_max_attempts=1),
        queue,
    )

    await service.process(None, _deadline())

    row = await _template_row(retrieval_pool, template_id)
    assert (row.enrichment_status, row.enrichment_error) == (
        "failed",
        "enrichment_batch_failed",
    )
    assert route.call_count == 1


async def test_a_scoped_sweep_does_not_enrich_templates(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    template_id = await _newbie_template(db_connection)
    route = mock_extraction(model_api, extraction_ok(EMPTY_OUTPUT))
    service = build_service(retrieval_pool, make_settings(), queue)

    await service.process(UUID(int=5), _deadline())

    assert (
        await _template_row(retrieval_pool, template_id)
    ).enrichment_status == "pending"
    assert route.call_count == 0


async def test_template_plans_ignore_commitments_and_scene(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    template_id = await _newbie_template(db_connection)
    async with retrieval_pool.connection() as connection:
        label = (await _spans(connection, template_id))[0].label
    output = {
        **EMPTY_OUTPUT,
        "scene": {"location": None, "present": [], "evidence": [label]},
    }
    mock_extraction(model_api, extraction_ok(output))
    service = build_service(retrieval_pool, make_settings(), queue)

    result = await service.process(None, _deadline())

    assert result.counts.items_dropped.get("template_scope_item", 0) >= 1
