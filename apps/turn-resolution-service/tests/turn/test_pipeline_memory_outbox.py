"""Pipeline-level tests: accepted_delta storage and memory_outbox rows are
written in the turn's own transaction, against a real test Postgres."""

import uuid

import pytest
from app.db.models.memory_outbox import MemoryOutbox
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from app.db.models.user import User
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.turn import pipeline
from app.turn.steps import ai_orchestrator
from google.genai import types
from session_factories import committed_factory
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")

_SNAPSHOT = {
    "mode": "master",
    "narrator_persona": "Dry humor.",
    "world_data": {},
    "state_schema": {
        "player": {
            "type": "object",
            "fields": {
                "health": {"type": "number", "min": 0, "max": 200, "initial": 100},
            },
        },
        "flags": {
            "type": "object",
            "fields": {"entered_cairn": {"type": "boolean", "initial": False}},
        },
    },
    "entities": [],
    "rule_invariants": [],
    "scenario_conditions": [],
    "end_conditions": [],
}
_ENTERED_CAIRN_ENDING = {
    "condition_expression": {"field": "flags.entered_cairn", "op": "==", "value": True},
    "outcome_tag": "win",
    "outcome_title": "The Threshold",
    "outcome_text": "You cross over.",
    "is_secret": False,
}


class _FakeCandidate:
    content = "fake-model-turn-content"


class _FakeResponse:
    def __init__(self, function_calls: list[types.FunctionCall], text: str) -> None:
        self.function_calls = function_calls
        self.text = text
        self.candidates = [_FakeCandidate()]


def _call(name: str, **args: object) -> types.FunctionCall:
    return types.FunctionCall(name=name, args=args)


def _fake_model(calls: list[types.FunctionCall], text: str = "The cairn hums."):
    async def _generate(system_instruction, contents, timeout_seconds, tools):
        yield _FakeResponse(calls, text)

    return _generate


async def _seed(
    session: AsyncSession,
    memory_publish_revision: int | None = 0,
    end_conditions: list[dict[str, object]] | None = None,
    scenario_conditions: list[dict[str, object]] | None = None,
) -> tuple[Playthrough, Participant]:
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    session.add(
        User(user_id=user_id, display_name="T", auth_provider_id=str(uuid.uuid4()))
    )
    await session.flush()
    session.add(
        Scenario(
            scenario_id=scenario_id,
            creator_id=user_id,
            title="Cairn",
            mode="master",
            complexity_tier="master",
            player_count_support="solo",
        )
    )
    await session.flush()
    playthrough = Playthrough(
        scenario_id=scenario_id,
        created_by=user_id,
        scenario_version=1,
        memory_publish_revision=memory_publish_revision,
        scenario_snapshot={
            **_SNAPSHOT,
            "end_conditions": end_conditions or [],
            "scenario_conditions": scenario_conditions or [],
        },
        state={
            "player": {"health": 100},
            "flags": {"entered_cairn": False},
            "narrative": {},
        },
    )
    session.add(playthrough)
    await session.flush()
    participant = Participant(
        playthrough_id=playthrough.playthrough_id,
        user_id=user_id,
        role="owner",
        turn_order_position=1,
    )
    session.add(participant)
    await session.flush()
    return playthrough, participant


async def _run(
    session: AsyncSession, playthrough: Playthrough, participant: Participant
) -> list[str]:
    response = await pipeline.run_turn(
        TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=playthrough.playthrough_id,
            participant_id=participant.participant_id,
            action_text="I enter the cairn.",
        ),
        await committed_factory(session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    return [event.event async for event in response.body_iterator]


async def _outbox_rows(
    session: AsyncSession, playthrough_id: uuid.UUID
) -> list[MemoryOutbox]:
    stmt = (
        select(MemoryOutbox)
        .where(MemoryOutbox.playthrough_id == playthrough_id)
        .order_by(MemoryOutbox.outbox_id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def _turn_logs(session: AsyncSession, playthrough_id: uuid.UUID) -> list[TurnLog]:
    stmt = select(TurnLog).where(TurnLog.playthrough_id == playthrough_id)
    return list((await session.execute(stmt)).scalars().all())


async def test_turn_stores_accepted_delta_and_writes_turn_outbox_row(
    db_session: AsyncSession, monkeypatch
) -> None:
    calls = [
        _call("adjust_numeric_field", path="player.health", delta=-10),
        _call("adjust_numeric_field", path="player.health", delta=-10),
        _call("set_field", path="player.health", value="high"),
        _call("propose_check", check_type="strength", difficulty_class=12),
        _call("set_field", path="flags.entered_cairn", value=True),
    ]
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _fake_model(calls)
    )
    playthrough, participant = await _seed(db_session)

    playthrough_id = playthrough.playthrough_id
    await _run(db_session, playthrough, participant)

    [turn_log] = await _turn_logs(db_session, playthrough_id)
    assert turn_log.accepted_delta == {
        "items": [
            {
                "kind": "state_mutation",
                "key": "player.health",
                "before": 100,
                "after": 80,
                "detail": {"tool_name": "adjust_numeric_field"},
            },
            {
                "kind": "state_mutation",
                "key": "flags.entered_cairn",
                "before": False,
                "after": True,
                "detail": {"tool_name": "set_field"},
            },
        ]
    }
    [row] = await _outbox_rows(db_session, playthrough_id)
    assert (row.item_kind, row.sequence, row.turn_id) == (
        "turn",
        1,
        turn_log.turn_id,
    )
    assert row.delivered_at is None
    assert [tc["is_valid"] for tc in turn_log.tool_calls] == [
        True,
        True,
        False,
        True,
        True,
    ]


async def test_legacy_playthrough_stores_delta_but_writes_no_outbox_row(
    db_session: AsyncSession, monkeypatch
) -> None:
    calls = [_call("set_field", path="flags.entered_cairn", value=True)]
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _fake_model(calls)
    )
    playthrough, participant = await _seed(db_session, memory_publish_revision=None)

    playthrough_id = playthrough.playthrough_id
    await _run(db_session, playthrough, participant)

    [turn_log] = await _turn_logs(db_session, playthrough_id)
    assert turn_log.accepted_delta["items"][0]["key"] == "flags.entered_cairn"
    assert await _outbox_rows(db_session, playthrough_id) == []


async def test_ending_writes_flush_row_with_the_turns_sequence(
    db_session: AsyncSession, monkeypatch
) -> None:
    calls = [_call("set_field", path="flags.entered_cairn", value=True)]
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _fake_model(calls)
    )
    playthrough, participant = await _seed(
        db_session, end_conditions=[_ENTERED_CAIRN_ENDING]
    )

    playthrough_id = playthrough.playthrough_id
    events = await _run(db_session, playthrough, participant)

    assert "playthrough_ended" in events
    rows = await _outbox_rows(db_session, playthrough_id)
    assert [(row.item_kind, row.sequence) for row in rows] == [
        ("turn", 1),
        ("flush", 1),
    ]
    await db_session.refresh(playthrough)
    assert playthrough.status == "completed"


async def test_ending_without_registration_writes_no_flush_row(
    db_session: AsyncSession, monkeypatch
) -> None:
    calls = [_call("set_field", path="flags.entered_cairn", value=True)]
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _fake_model(calls)
    )
    playthrough, participant = await _seed(
        db_session, memory_publish_revision=None, end_conditions=[_ENTERED_CAIRN_ENDING]
    )

    playthrough_id = playthrough.playthrough_id
    events = await _run(db_session, playthrough, participant)

    assert "playthrough_ended" in events
    assert await _outbox_rows(db_session, playthrough_id) == []


async def test_failed_flush_write_rolls_back_the_ending_but_keeps_the_turn(
    db_session: AsyncSession, monkeypatch
) -> None:
    calls = [_call("set_field", path="flags.entered_cairn", value=True)]
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _fake_model(calls)
    )

    async def _raise(*args, **kwargs):
        raise SQLAlchemyError("simulated flush insert failure")

    monkeypatch.setattr(MemoryOutboxRepo, "add_flush_row", _raise)
    playthrough, participant = await _seed(
        db_session, end_conditions=[_ENTERED_CAIRN_ENDING]
    )

    playthrough_id = playthrough.playthrough_id
    events = await _run(db_session, playthrough, participant)

    assert "playthrough_ended" not in events
    assert events[-1] == "done"
    rows = await _outbox_rows(db_session, playthrough_id)
    assert [(row.item_kind, row.sequence) for row in rows] == [("turn", 1)]
    await db_session.refresh(playthrough)
    assert playthrough.status == "active"
    assert playthrough.ended_outcome_title is None
    assert playthrough.turn_count == 1


_BLEEDING_CONDITION = {
    "condition_id": "bleeding",
    "label": "Bleeding",
    "condition_expression": {"field": "player.health", "op": "==", "value": 100},
    "narrator_instruction": "The player bleeds.",
    "state_mutation": {"path": "player.health", "op": "decrement", "value": 5},
}


async def test_effect_c_change_is_stored_as_an_automatic_effect_item(
    db_session: AsyncSession, monkeypatch
) -> None:
    calls = [_call("set_field", path="flags.entered_cairn", value=True)]
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _fake_model(calls)
    )
    playthrough, participant = await _seed(
        db_session, scenario_conditions=[_BLEEDING_CONDITION]
    )

    playthrough_id = playthrough.playthrough_id
    await _run(db_session, playthrough, participant)

    [turn_log] = await _turn_logs(db_session, playthrough_id)
    assert [
        (item["kind"], item["key"], item["before"], item["after"])
        for item in turn_log.accepted_delta["items"]
    ] == [
        ("automatic_effect", "player.health", 100, 95),
        ("state_mutation", "flags.entered_cairn", False, True),
    ]
    assert turn_log.accepted_delta["items"][0]["detail"] == {"source": "condition"}
