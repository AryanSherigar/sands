"""Degraded reasons: failed extraction, indexing lag and a missing template."""

from uuid import uuid4

from app.models.templates import PlaythroughRow
from app.repositories import playthrough_repo
from app.services.degraded_service import compute_degraded_reasons, is_indexing_lagging
from psycopg import AsyncConnection
from tests.repositories.helpers_evidence import make_playthrough, make_template
from tests.services.retrieval_service_helpers import add_batch

WINDOW = 6


async def reasons_for(
    connection: AsyncConnection, playthrough: PlaythroughRow, window: int = WINDOW
) -> list[str]:
    fresh = await playthrough_repo.get_playthrough(
        connection, playthrough.playthrough_id
    )
    assert fresh is not None
    return await compute_degraded_reasons(connection, fresh, recent_window_turns=window)


async def make_healthy(connection: AsyncConnection) -> PlaythroughRow:
    template = await make_template(connection)
    return await make_playthrough(connection, template_id=template.template_id)


async def test_a_healthy_playthrough_has_no_reasons(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_healthy(db_connection)

    assert await reasons_for(db_connection, playthrough) == []


async def test_a_failed_batch_reports_extraction_failed(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_healthy(db_connection)
    await add_batch(db_connection, playthrough.playthrough_id, "failed")

    assert await reasons_for(db_connection, playthrough) == ["extraction_failed"]


async def test_only_a_failed_status_counts(db_connection: AsyncConnection) -> None:
    playthrough = await make_healthy(db_connection)
    for status in ("pending", "running", "extracted", "applied"):
        await add_batch(db_connection, playthrough.playthrough_id, status)

    assert await reasons_for(db_connection, playthrough) == []


async def test_a_failed_batch_of_another_playthrough_is_ignored(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_healthy(db_connection)
    other = await make_healthy(db_connection)
    await add_batch(db_connection, other.playthrough_id, "failed")

    assert await reasons_for(db_connection, playthrough) == []


async def test_lag_above_the_window_reports_indexing_lag_and_equal_does_not(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_healthy(db_connection)
    await playthrough_repo.advance_watermarks(
        db_connection, playthrough.playthrough_id, latest_seq_seen=10, indexed_seq=4
    )
    assert await reasons_for(db_connection, playthrough, window=6) == []
    assert await reasons_for(db_connection, playthrough, window=5) == ["indexing_lag"]
    assert await reasons_for(db_connection, playthrough, window=0) == ["indexing_lag"]


async def test_a_null_template_reports_template_missing(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection, template_id=None)

    assert await reasons_for(db_connection, playthrough) == ["template_missing"]


async def test_a_template_id_without_a_template_row_reports_template_missing(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_healthy(db_connection)
    orphaned = playthrough.model_copy(update={"template_id": uuid4()})

    reasons = await compute_degraded_reasons(
        db_connection, orphaned, recent_window_turns=WINDOW
    )

    assert reasons == ["template_missing"]


async def test_reasons_come_in_the_fixed_order(db_connection: AsyncConnection) -> None:
    playthrough = await make_playthrough(db_connection, template_id=None)
    await add_batch(db_connection, playthrough.playthrough_id, "failed")
    await playthrough_repo.advance_watermarks(
        db_connection, playthrough.playthrough_id, latest_seq_seen=50
    )

    assert await reasons_for(db_connection, playthrough) == [
        "extraction_failed",
        "indexing_lag",
        "template_missing",
    ]


def test_indexing_lag_is_pure_arithmetic_on_the_watermarks() -> None:
    row = PlaythroughRow(
        playthrough_id=uuid4(),
        template_id=None,
        ingested_seq=0,
        indexed_seq=3,
        extracted_seq=0,
        latest_seq_seen=9,
        flush_requested_through_seq=None,
        created_at="2026-10-27T00:00:00Z",
    )

    assert is_indexing_lagging(row, 5) is True
    assert is_indexing_lagging(row, 6) is False
