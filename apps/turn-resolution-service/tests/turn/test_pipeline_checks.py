"""Integration tests for the propose_check / check_resolution flow wired
into the turn pipeline. Mirrors test_pipeline_minigames.py's conventions:
mocks Gemini via ai_orchestrator.narration_router.stream_with_tools, runs
against a real test Postgres (db_session), never mocks the database.
"""

import json
import uuid

import pytest
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from app.db.models.user import User
from app.exceptions.turn_exceptions import CheckResolutionRequiredError
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.turn import pipeline
from app.turn.steps import ai_orchestrator
from google.genai import types
from session_factories import committed_factory
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _FakeResponse:
    def __init__(
        self, function_calls: list[types.FunctionCall], text: str | None
    ) -> None:
        self.function_calls = function_calls
        self.text = text


def _fake_stream(*responses: _FakeResponse):
    async def _generate(system_instruction, contents, timeout_seconds, tools):
        for response in responses:
            yield response

    return _generate


async def _seed_master_playthrough(
    session: AsyncSession,
    state_overrides: dict[str, object] | None = None,
) -> tuple[Playthrough, Participant]:
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    user = User(
        user_id=user_id, display_name="Tester", auth_provider_id=str(uuid.uuid4())
    )
    scenario = Scenario(
        scenario_id=scenario_id,
        creator_id=user_id,
        title="The Hollow Cairn",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
    )
    state = {
        "player": {"health": 100},
        "narrative": {},
    }
    state.update(state_overrides or {})
    playthrough = Playthrough(
        scenario_id=scenario_id,
        created_by=user_id,
        scenario_version=1,
        scenario_snapshot={
            "mode": "master",
            "narrator_persona": "Dry, weary humor.",
            "world_data": {},
            "state_schema": {
                "player": {
                    "type": "object",
                    "fields": {"health": {"type": "number", "min": 0, "max": 100}},
                },
            },
            "entities": [],
            "rule_invariants": [],
            "scenario_conditions": [],
            "end_conditions": [],
        },
        state=state,
    )
    session.add(user)
    await session.flush()
    session.add(scenario)
    await session.flush()
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


async def _load_playthrough(
    session: AsyncSession, playthrough_id: uuid.UUID
) -> Playthrough:
    stmt = (
        select(Playthrough)
        .execution_options(populate_existing=True)
        .where(Playthrough.playthrough_id == playthrough_id)
    )
    result = (await session.execute(stmt)).scalars().first()
    assert result is not None
    return result


async def test_propose_check_yields_event_and_stamps_pending_state(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_stream(
            _FakeResponse([], "The lock looks tricky. This calls for finesse."),
            _FakeResponse(
                [
                    types.FunctionCall(
                        name="propose_check",
                        args={
                            "check_type": "lockpicking",
                            "difficulty_class": 15,
                            "reasoning": "The mechanism is old and delicate.",
                        },
                    )
                ],
                None,
            ),
        ),
    )
    playthrough, participant = await _seed_master_playthrough(db_session)

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I try to pick the lock.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    assert [e.event for e in events] == ["narration", "turn_summary", "check", "done"]
    check_event = next(e for e in events if e.event == "check")
    payload = json.loads(check_event.data)
    assert payload["check_type"] == "lockpicking"
    assert payload["difficulty_class"] == 15
    assert payload["reasoning"] == "The mechanism is old and delicate."
    assert isinstance(payload["check_id"], str) and payload["check_id"]

    updated = await _load_playthrough(db_session, playthrough.playthrough_id)
    pending = updated.state["_pending_check"]
    assert pending["check_type"] == "lockpicking"
    assert pending["proposing_participant_id"] == str(participant.participant_id)
    assert pending["resolved_roll"] is None


async def test_narrative_action_blocked_while_check_pending(
    db_session: AsyncSession,
) -> None:
    playthrough, participant = await _seed_master_playthrough(
        db_session,
        state_overrides={
            "_pending_check": {
                "check_id": "check-1",
                "check_type": "lockpicking",
                "difficulty_class": 15,
                "proposing_participant_id": str(uuid.uuid4()),
                "resolved_roll": None,
            }
        },
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I do something else entirely.",
    )

    with pytest.raises(CheckResolutionRequiredError):
        await pipeline.run_turn(
            turn_input,
            await committed_factory(db_session),
            CurrentUser(user_id=participant.user_id, token_version=1),
        )


async def test_check_attempt_persists_roll_and_narrates_outcome(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_stream(_FakeResponse([], "Your fingers find the tumblers.")),
    )
    playthrough, participant = await _seed_master_playthrough(db_session)
    playthrough.state["_pending_check"] = {
        "check_id": "check-1",
        "check_type": "lockpicking",
        "difficulty_class": 15,
        "proposing_participant_id": str(participant.participant_id),
        "resolved_roll": None,
    }
    flag_modified(playthrough, "state")
    await db_session.flush()

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="",
        action_kind="check_resolution",
        check_resolution={"check_id": "check-1", "resolution": "attempt"},
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    assert [e.event for e in events][:2] == ["check_resolved", "narration"]
    resolved_payload = json.loads(events[0].data)
    assert resolved_payload["check_type"] == "lockpicking"
    assert 1 <= resolved_payload["resolved_roll"] <= 20
    assert resolved_payload["is_success"] == (resolved_payload["resolved_roll"] >= 15)

    updated = await _load_playthrough(db_session, playthrough.playthrough_id)
    assert "_pending_check" not in updated.state


async def test_check_attempt_reuses_already_persisted_roll_on_retry(
    db_session: AsyncSession, monkeypatch
) -> None:
    """Simulates a dropped connection after the early roll commit: the
    second attempt submission must reuse the same roll, never reroll."""
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_stream(_FakeResponse([], "Your fingers find the tumblers.")),
    )
    playthrough, participant = await _seed_master_playthrough(db_session)
    playthrough.state["_pending_check"] = {
        "check_id": "check-1",
        "check_type": "lockpicking",
        "difficulty_class": 15,
        "proposing_participant_id": str(participant.participant_id),
        "resolved_roll": 7,
    }
    flag_modified(playthrough, "state")
    await db_session.flush()

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="",
        action_kind="check_resolution",
        check_resolution={"check_id": "check-1", "resolution": "attempt"},
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    resolved_payload = json.loads(events[0].data)
    assert resolved_payload["resolved_roll"] == 7
    assert resolved_payload["is_success"] is False


async def test_check_decline_resolves_with_no_roll(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_stream(
            _FakeResponse([], "You step back from the lock, unwilling to risk it.")
        ),
    )
    playthrough, participant = await _seed_master_playthrough(db_session)
    playthrough.state["_pending_check"] = {
        "check_id": "check-1",
        "check_type": "lockpicking",
        "difficulty_class": 15,
        "proposing_participant_id": str(participant.participant_id),
        "resolved_roll": None,
    }
    flag_modified(playthrough, "state")
    await db_session.flush()

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="",
        action_kind="check_resolution",
        check_resolution={"check_id": "check-1", "resolution": "decline"},
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    resolved_payload = json.loads(events[0].data)
    assert resolved_payload["resolved_roll"] is None
    assert resolved_payload["is_success"] is None

    updated = await _load_playthrough(db_session, playthrough.playthrough_id)
    assert "_pending_check" not in updated.state


async def _delta_items(
    session: AsyncSession, playthrough_id: uuid.UUID
) -> list[dict[str, object]]:
    stmt = select(TurnLog).where(TurnLog.playthrough_id == playthrough_id)
    turn_log = (await session.execute(stmt)).scalars().one()
    return turn_log.accepted_delta["items"]


async def _resolve_check(
    session: AsyncSession,
    monkeypatch,
    resolution: str,
    resolved_roll: int | None,
) -> list[dict[str, object]]:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_stream(_FakeResponse([], "The lock gives.")),
    )
    playthrough, participant = await _seed_master_playthrough(session)
    playthrough.state["_pending_check"] = {
        "check_id": "check-1",
        "check_type": "lockpicking",
        "difficulty_class": 15,
        "proposing_participant_id": str(participant.participant_id),
        "resolved_roll": resolved_roll,
    }
    flag_modified(playthrough, "state")
    await session.flush()
    playthrough_id = playthrough.playthrough_id
    response = await pipeline.run_turn(
        TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=playthrough_id,
            participant_id=participant.participant_id,
            action_text="",
            action_kind="check_resolution",
            check_resolution={"check_id": "check-1", "resolution": resolution},
        ),
        await committed_factory(session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    [event async for event in response.body_iterator]
    return await _delta_items(session, playthrough_id)


async def test_check_attempt_is_stored_as_a_roll_delta_item(
    db_session: AsyncSession, monkeypatch
) -> None:
    items = await _resolve_check(db_session, monkeypatch, "attempt", 17)

    assert items == [
        {
            "kind": "roll",
            "key": "check-1",
            "before": None,
            "after": 17,
            "detail": {
                "check_type": "lockpicking",
                "difficulty_class": 15,
                "is_success": True,
            },
        }
    ]


async def test_check_decline_stores_no_roll_delta_item(
    db_session: AsyncSession, monkeypatch
) -> None:
    items = await _resolve_check(db_session, monkeypatch, "decline", None)

    assert items == []
