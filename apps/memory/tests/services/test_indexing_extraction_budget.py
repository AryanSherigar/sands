"""process_pending: embedding first within a capped share, extraction with the rest."""

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from app.models.extraction import ExtractionCounts
from app.models.process_pending import ProcessPendingRequest
from app.services.extraction_runtime import ExtractionStepResult
from app.services.indexing_service import IndexingService
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.services.indexing_helpers import (
    FakeEmbedder,
    add_span,
    make_settings,
    make_world,
)

TOTAL_SECONDS = 10
SHARE = 0.6
TOLERANCE_SECONDS = 1.0


class FakeExtraction:
    def __init__(
        self, *, is_configured: bool = True, errors: list[str] | None = None
    ) -> None:
        self.is_configured = is_configured
        self.calls: list[tuple[UUID | None, float]] = []
        self._errors = errors or []

    async def process(
        self, playthrough_id: UUID | None, deadline_monotonic: float
    ) -> ExtractionStepResult:
        self.calls.append((playthrough_id, deadline_monotonic))
        counts = ExtractionCounts(batches_applied=2)
        return ExtractionStepResult("completed", counts, self._errors)


@pytest.fixture
async def pool(migrated_test_database_url: str) -> AsyncIterator[AsyncConnectionPool]:
    connection_pool = AsyncConnectionPool(
        migrated_test_database_url, max_size=5, open=False
    )
    await connection_pool.open()
    yield connection_pool
    await connection_pool.close()


def _service(
    pool: AsyncConnectionPool,
    embedder: FakeEmbedder | None,
    extraction: FakeExtraction | None,
) -> IndexingService:
    settings = make_settings(embedding_deadline_share=SHARE)
    return IndexingService(pool, settings, embedder, extraction)  # type: ignore[arg-type]


async def test_embedding_is_capped_to_its_share_and_extraction_gets_the_rest(
    db_connection: AsyncConnection, pool: AsyncConnectionPool
) -> None:
    world = await make_world(db_connection)
    await add_span(
        db_connection, "playthrough", world.playthrough_id, 1, "text to embed"
    )
    embedder, extraction = FakeEmbedder(), FakeExtraction()

    await _service(pool, embedder, extraction).process_pending(
        ProcessPendingRequest(deadline_seconds=TOTAL_SECONDS)
    )

    embedding_deadline = embedder.deadlines[0]
    assert embedding_deadline is not None
    _, extraction_deadline = extraction.calls[0]
    gap = extraction_deadline - embedding_deadline
    assert gap == pytest.approx(TOTAL_SECONDS * (1 - SHARE), abs=TOLERANCE_SECONDS)


async def test_without_a_configured_extraction_embedding_keeps_the_full_deadline(
    db_connection: AsyncConnection, pool: AsyncConnectionPool
) -> None:
    world = await make_world(db_connection)
    await add_span(
        db_connection, "playthrough", world.playthrough_id, 1, "text to embed"
    )
    embedder, extraction = FakeEmbedder(), FakeExtraction(is_configured=False)

    await _service(pool, embedder, extraction).process_pending(
        ProcessPendingRequest(deadline_seconds=TOTAL_SECONDS)
    )

    _, extraction_deadline = extraction.calls[0]
    assert embedder.deadlines[0] == pytest.approx(
        extraction_deadline, abs=TOLERANCE_SECONDS
    )


async def test_unconfigured_embedding_still_runs_extraction(
    pool: AsyncConnectionPool,
) -> None:
    extraction = FakeExtraction()

    response = await _service(pool, None, extraction).process_pending()

    assert response.embedding_step == "unconfigured"
    assert response.extraction_step == "completed"
    assert len(extraction.calls) == 1


async def test_response_carries_extraction_counts_and_merged_errors(
    pool: AsyncConnectionPool,
) -> None:
    extraction = FakeExtraction(errors=["extraction_rate_limited"])

    response = await _service(pool, FakeEmbedder(), extraction).process_pending()

    assert response.extraction_counts.batches_applied == 2
    assert response.errors == ["extraction_rate_limited"]


async def test_playthrough_scope_is_passed_to_extraction(
    pool: AsyncConnectionPool,
) -> None:
    extraction = FakeExtraction()
    playthrough_id = UUID(int=7)

    await _service(pool, FakeEmbedder(), extraction).process_pending(
        ProcessPendingRequest(playthrough_id=playthrough_id)
    )

    assert extraction.calls[0][0] == playthrough_id


async def test_without_an_extraction_service_the_response_reports_idle(
    pool: AsyncConnectionPool,
) -> None:
    response = await _service(pool, FakeEmbedder(), None).process_pending()

    assert response.extraction_step == "idle"
    assert response.extraction_counts == ExtractionCounts()
