"""Inline memory delivery inside the turn pipeline, against a real test Postgres.

The autouse conftest stub disables delivery; these tests re-install the real
step with a relay bound to the test database.
"""

import asyncio
import time
import uuid
from datetime import timedelta

import pytest
from app.config import settings
from app.db.models.memory_relay_claim import MemoryRelayClaim
from app.exceptions.memory_exceptions import MemoryIngestError
from app.integrations import memory_client
from app.models.auth import CurrentUser
from app.models.memory_ingest import IngestResponse
from app.models.turn import TurnRequestInput
from app.services import memory_relay_service
from app.services.memory_relay_service import MemoryRelayService
from app.turn import pipeline
from app.turn.steps import ai_orchestrator, memory_delivery
from memory_outbox_factories import SeededPlaythrough, reload_rows
from session_factories import committed_factory
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from test_pipeline_memory_outbox import _fake_model, _seed

pytestmark = pytest.mark.asyncio(loop_scope="session")

REAL_DELIVER_AFTER_COMMIT = memory_delivery.deliver_after_commit


@pytest.fixture
def real_delivery(monkeypatch, test_engine):
    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    monkeypatch.setattr(
        memory_relay_service, "_relay_service", MemoryRelayService(factory)
    )
    monkeypatch.setattr(
        memory_delivery, "deliver_after_commit", REAL_DELIVER_AFTER_COMMIT
    )


def _ok(request) -> IngestResponse:
    return IngestResponse(
        playthrough_id=request.playthrough_id,
        ingested_seq=1,
        latest_seq_seen=1,
        items=[
            {"item_kind": i.item_kind, "sequence": i.sequence, "outcome": "applied"}
            for i in request.items
        ],
    )


async def _run_turn(db_session: AsyncSession, monkeypatch, memory_publish_revision=0):
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _fake_model([])
    )
    playthrough, participant = await _seed(
        db_session, memory_publish_revision=memory_publish_revision
    )
    seeded = SeededPlaythrough(
        playthrough.playthrough_id,
        playthrough.scenario_id,
        participant.participant_id,
        participant.user_id,
    )
    response = await pipeline.run_turn(
        TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=seeded.playthrough_id,
            participant_id=seeded.participant_id,
            action_text="I wait.",
        ),
        await committed_factory(db_session),
        CurrentUser(user_id=seeded.user_id, token_version=1),
    )
    events = [event.event async for event in response.body_iterator]
    return seeded, events


async def test_inline_delivery_marks_the_turn_delivered_before_done(
    db_session: AsyncSession, real_delivery, monkeypatch
) -> None:
    async def _ingest(request):
        return _ok(request)

    monkeypatch.setattr(memory_client, "ingest_items", _ingest)

    seeded, events = await _run_turn(db_session, monkeypatch)

    assert events[-1] == "done"
    [row] = await reload_rows(db_session, seeded)
    assert (row.item_kind, row.delivered_at is not None) == ("turn", True)


async def test_memory_down_still_emits_done_and_leaves_the_row_for_the_sweep(
    db_session: AsyncSession, real_delivery, monkeypatch
) -> None:
    async def _down(request):
        raise MemoryIngestError("unavailable")

    monkeypatch.setattr(memory_client, "ingest_items", _down)

    seeded, events = await _run_turn(db_session, monkeypatch)

    assert events[-1] == "done"
    [row] = await reload_rows(db_session, seeded)
    assert (row.delivered_at, row.attempt_count, row.last_error) == (
        None,
        1,
        "0:unavailable",
    )


async def test_hung_memory_is_cut_off_and_recovers_after_claim_expiry(
    db_session: AsyncSession, real_delivery, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "memory_delivery_timeout_seconds", 0.2)

    async def _hang(request):
        await asyncio.sleep(30)

    monkeypatch.setattr(memory_client, "ingest_items", _hang)

    started = time.monotonic()
    seeded, events = await _run_turn(db_session, monkeypatch)
    elapsed = time.monotonic() - started

    assert events[-1] == "done"
    assert elapsed < 5
    [row] = await reload_rows(db_session, seeded)
    assert row.delivered_at is None

    async def _ingest(request):
        return _ok(request)

    monkeypatch.setattr(memory_client, "ingest_items", _ingest)
    relay = memory_relay_service.get_relay_service()
    assert (await relay.deliver_playthrough(seeded.playthrough_id)).rows_delivered == 0
    await db_session.execute(
        update(MemoryRelayClaim)
        .where(MemoryRelayClaim.playthrough_id == seeded.playthrough_id)
        .values(lease_expires_at=func.now() - timedelta(seconds=1))
    )
    await db_session.commit()
    summary = await memory_relay_service.get_relay_service().deliver_playthrough(
        seeded.playthrough_id
    )
    assert summary.rows_delivered == 1


async def test_unexpected_delivery_error_never_reaches_the_client(
    db_session: AsyncSession, real_delivery, monkeypatch
) -> None:
    async def _explode(request):
        raise RuntimeError("bug in delivery")

    monkeypatch.setattr(memory_client, "ingest_items", _explode)

    seeded, events = await _run_turn(db_session, monkeypatch)

    assert events[-1] == "done"
    [row] = await reload_rows(db_session, seeded)
    assert row.delivered_at is None


async def test_legacy_playthrough_never_calls_the_relay(
    db_session: AsyncSession, real_delivery, monkeypatch
) -> None:
    calls: list[object] = []

    async def _ingest(request):
        calls.append(request)
        return _ok(request)

    monkeypatch.setattr(memory_client, "ingest_items", _ingest)

    seeded, events = await _run_turn(
        db_session, monkeypatch, memory_publish_revision=None
    )

    assert events[-1] == "done"
    assert calls == []
    assert await reload_rows(db_session, seeded) == []
