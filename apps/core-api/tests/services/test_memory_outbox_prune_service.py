"""Tests for app/services/memory_outbox_prune_service.py."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.config import settings
from app.db.models.memory_outbox import ITEM_KIND_TURN, MemoryOutbox
from app.repositories.memory_outbox_repo import (
    DEAD_LETTER_ERROR_CODES,
    MemoryOutboxRepo,
)
from app.services.memory_outbox_prune_service import prune_delivered_outbox
from sqlalchemy import select

NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)
OLD = NOW - timedelta(days=settings.memory_outbox_retention_days + 1)
RECENT = NOW - timedelta(days=1)


async def _add_row(
    db_session,
    sequence: int,
    delivered_at: datetime | None,
    last_error: str | None = None,
    playthrough_id: uuid.UUID | None = None,
) -> MemoryOutbox:
    row = MemoryOutbox(
        playthrough_id=playthrough_id or uuid.uuid4(),
        item_kind=ITEM_KIND_TURN,
        sequence=sequence,
        delivered_at=delivered_at,
        last_error=last_error,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _remaining_ids(db_session) -> set[int]:
    result = await db_session.execute(select(MemoryOutbox.outbox_id))
    return set(result.scalars().all())


async def _empty_outbox(db_session) -> None:
    await db_session.rollback()
    await db_session.execute(MemoryOutbox.__table__.delete())
    await db_session.commit()


@pytest.fixture(autouse=True)
async def clean_outbox(db_session):
    """Other suites commit outbox rows; start and end empty so counts are exact."""
    await _empty_outbox(db_session)
    yield
    await _empty_outbox(db_session)


@pytest.mark.asyncio
async def test_it_deletes_only_old_delivered_rows(db_session) -> None:
    old_delivered = await _add_row(db_session, 1, OLD)
    old_after_failure = await _add_row(db_session, 2, OLD, last_error="503:db_down")
    recent_delivered = await _add_row(db_session, 3, RECENT)
    undelivered = await _add_row(db_session, 4, None)
    old_undelivered_failing = await _add_row(db_session, 5, None, "503:db_down")

    result = await prune_delivered_outbox(db_session, is_dry_run=False, now=NOW)

    assert result.row_count == 2
    assert await _remaining_ids(db_session) == {
        recent_delivered.outbox_id,
        undelivered.outbox_id,
        old_undelivered_failing.outbox_id,
    }
    assert old_delivered.outbox_id not in await _remaining_ids(db_session)
    assert old_after_failure.outbox_id not in await _remaining_ids(db_session)


@pytest.mark.asyncio
@pytest.mark.parametrize("error_code", DEAD_LETTER_ERROR_CODES)
async def test_it_keeps_dead_lettered_orphans(db_session, error_code: str) -> None:
    orphan = await _add_row(db_session, 1, OLD, last_error=error_code)

    result = await prune_delivered_outbox(db_session, is_dry_run=False, now=NOW)

    assert result.row_count == 0
    assert await _remaining_ids(db_session) == {orphan.outbox_id}


@pytest.mark.asyncio
async def test_dry_run_counts_without_deleting(db_session) -> None:
    await _add_row(db_session, 1, OLD)
    await _add_row(db_session, 2, OLD)

    result = await prune_delivered_outbox(db_session, is_dry_run=True, now=NOW)

    assert (result.row_count, result.is_dry_run) == (2, True)
    assert len(await _remaining_ids(db_session)) == 2


@pytest.mark.asyncio
async def test_it_deletes_across_more_than_one_batch(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "account_purge_batch_size", 2)
    playthrough_id = uuid.uuid4()
    for sequence in range(5):
        await _add_row(db_session, sequence, OLD, playthrough_id=playthrough_id)

    result = await prune_delivered_outbox(db_session, is_dry_run=False, now=NOW)

    assert result.row_count == 5
    assert await _remaining_ids(db_session) == set()


@pytest.mark.asyncio
async def test_repo_count_matches_what_delete_would_remove(db_session) -> None:
    await _add_row(db_session, 1, OLD)
    await _add_row(db_session, 2, RECENT)
    repo = MemoryOutboxRepo(db_session)

    assert await repo.count_delivered_before(NOW - timedelta(days=7)) == 1
