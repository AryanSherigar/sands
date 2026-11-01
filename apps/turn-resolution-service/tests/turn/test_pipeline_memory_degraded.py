"""memory_degraded SSE event: emitted before done when memory is behind."""

import json
import uuid

import pytest
from app.db.models.memory_outbox import MemoryOutbox
from app.integrations import memory_client
from app.models.auth import CurrentUser
from app.models.memory import RetrieveResponse, Watermarks
from app.models.turn import TurnRequestInput
from app.turn import pipeline
from app.turn.steps import ai_orchestrator, memory_degraded
from session_factories import committed_factory
from sqlalchemy.ext.asyncio import AsyncSession
from test_pipeline_memory_outbox import _fake_model, _seed

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _retrieve_with(reasons: list[str]):
    async def _retrieve(request):
        return RetrieveResponse(
            items=[],
            active_entities=[],
            scene=None,
            watermarks=Watermarks(
                ingested_seq=0, indexed_seq=0, extracted_seq=0, latest_seq_seen=0
            ),
            degraded_reasons=reasons,
            embedding_model="test-embedding",
        )

    return _retrieve


async def _run(db_session: AsyncSession, monkeypatch, *, revision, reasons):
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _fake_model([])
    )
    monkeypatch.setattr(memory_client, "retrieve", _retrieve_with(reasons))
    playthrough, participant = await _seed(db_session, memory_publish_revision=revision)
    response = await pipeline.run_turn(
        TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=playthrough.playthrough_id,
            participant_id=participant.participant_id,
            action_text="I wait.",
        ),
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    return playthrough, [event async for event in response.body_iterator]


def _names(events) -> list[str]:
    return [event.event for event in events]


async def test_memory_reasons_are_emitted_before_done(
    db_session: AsyncSession, monkeypatch
) -> None:
    _, events = await _run(
        db_session, monkeypatch, revision=0, reasons=["extraction_failed"]
    )

    names = _names(events)
    assert names[-1] == "done"
    assert names[-2] == "memory_degraded"
    payload = json.loads(events[-2].data)
    assert payload == {"reasons": ["extraction_failed"]}


async def test_no_event_when_memory_is_healthy(
    db_session: AsyncSession, monkeypatch
) -> None:
    _, events = await _run(db_session, monkeypatch, revision=0, reasons=[])

    assert "memory_degraded" not in _names(events)
    assert _names(events)[-1] == "done"


async def test_legacy_playthroughs_never_report_degraded(
    db_session: AsyncSession, monkeypatch
) -> None:
    _, events = await _run(
        db_session, monkeypatch, revision=None, reasons=["retrieval_failed"]
    )

    assert "memory_degraded" not in _names(events)


async def test_unreachable_memory_reports_retrieval_failed(
    db_session: AsyncSession, monkeypatch
) -> None:
    async def _down(request):
        raise RuntimeError("down")

    monkeypatch.setattr(memory_client, "retrieve", _down)
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _fake_model([])
    )
    playthrough, participant = await _seed(db_session, memory_publish_revision=0)
    response = await pipeline.run_turn(
        TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=playthrough.playthrough_id,
            participant_id=participant.participant_id,
            action_text="I wait.",
        ),
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    degraded = [e for e in events if e.event == "memory_degraded"]
    assert [json.loads(e.data)["reasons"] for e in degraded] == [["retrieval_failed"]]


async def test_delivery_lag_when_old_rows_are_still_undelivered(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(memory_degraded.settings, "recent_window_turns", 2)
    playthrough, participant = await _seed(db_session, memory_publish_revision=0)
    db_session.add(
        MemoryOutbox(
            playthrough_id=playthrough.playthrough_id,
            item_kind="turn",
            sequence=1,
            turn_id=uuid.uuid4(),
            payload={},
        )
    )
    await db_session.flush()
    playthrough.turn_count = 3
    await db_session.flush()
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _fake_model([])
    )
    monkeypatch.setattr(memory_client, "retrieve", _retrieve_with([]))

    response = await pipeline.run_turn(
        TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=playthrough.playthrough_id,
            participant_id=participant.participant_id,
            action_text="I wait.",
        ),
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    degraded = [e for e in events if e.event == "memory_degraded"]
    assert [json.loads(e.data)["reasons"] for e in degraded] == [["delivery_lag"]]
