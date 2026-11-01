"""Integration tests for minigame trigger/result-resolution wired into the
turn pipeline. Mirrors test_pipeline_end_conditions.py's conventions: mocks
Gemini via ai_orchestrator.narration_router.stream_with_tools, runs against a
real test Postgres (db_session), never mocks the database.
"""

import json
import uuid

import pytest
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.exceptions.turn_exceptions import (
    MinigameResultMismatchError,
    MinigameResultRequiredError,
)
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.turn import pipeline
from app.turn.steps import ai_orchestrator, end_condition_evaluator
from google.genai import types
from session_factories import committed_factory
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _FakeCandidate:
    def __init__(self) -> None:
        self.content = "fake-model-turn-content"


class _FakeResponse:
    def __init__(self, function_calls: list[types.FunctionCall], text: str) -> None:
        self.function_calls = function_calls
        self.text = text
        self.candidates = [_FakeCandidate()]


def _fake_narration(text: str):
    async def _generate(system_instruction, contents, timeout_seconds, tools):
        yield _FakeResponse([], text)

    return _generate


_WARDENS_ONSLAUGHT = {
    "minigame_id": "mg-wardens-onslaught",
    "minigame_type": "dodge",
    "label": "Warden's Onslaught",
    "trigger_condition_expression": {
        "field": "the_warden.health",
        "op": "<=",
        "value": 0,
    },
    "priority": 0,
    "outcome_mode": "binary",
    "win_mutation": {"path": "flags.tactical_advantage", "op": "set", "value": True},
    "lose_mutation": {"path": "player.health", "op": "decrement", "value": 15},
    "tiered_outcomes": [],
    "timeout_mutation": {"path": "player.health", "op": "decrement", "value": 5},
    "narrator_instruction_template": "The onslaught concludes: {outcome_tag}.",
    "dodge_config": {"difficulty": 3},
}

_STATE_SCHEMA = {
    "player": {"type": "object", "fields": {"health": {"type": "number"}}},
    "flags": {"type": "object", "fields": {"tactical_advantage": {"type": "boolean"}}},
    "the_warden": {"type": "object", "fields": {"health": {"type": "number"}}},
}

_WARDEN_DEFEATED_END_CONDITION = {
    "condition_expression": {"field": "the_warden.health", "op": "<=", "value": 0},
    "outcome_tag": "win",
    "outcome_title": "The Ashen Ending",
    "outcome_text": "The Warden kneels.",
    "is_secret": False,
}


async def _seed_master_playthrough(
    session: AsyncSession,
    scenario_minigames: list[dict[str, object]],
    end_conditions: list[dict[str, object]] | None = None,
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
        "the_warden": {"health": 0},
        "player": {"health": 100},
        "flags": {"tactical_advantage": False},
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
            "state_schema": _STATE_SCHEMA,
            "entities": [],
            "rule_invariants": [],
            "scenario_conditions": [],
            "end_conditions": end_conditions or [],
            "scenario_minigames": scenario_minigames,
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


async def _add_second_participant(
    session: AsyncSession, playthrough_id: uuid.UUID
) -> Participant:
    second_user_id = uuid.uuid4()
    session.add(
        User(
            user_id=second_user_id,
            display_name="Second Tester",
            auth_provider_id=str(uuid.uuid4()),
        )
    )
    await session.flush()
    participant_two = Participant(
        playthrough_id=playthrough_id,
        user_id=second_user_id,
        role="joined",
        turn_order_position=2,
    )
    session.add(participant_two)
    await session.flush()
    return participant_two


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


async def test_minigame_trigger_yields_event_and_stamps_pending_state(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_narration("The Warden staggers and falls."),
    )
    playthrough, participant = await _seed_master_playthrough(
        db_session, [_WARDENS_ONSLAUGHT]
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I strike the final blow.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    assert [e.event for e in events] == [
        "narration",
        "turn_summary",
        "minigame",
        "done",
    ]
    minigame_event = next(e for e in events if e.event == "minigame")
    payload = json.loads(minigame_event.data)
    assert payload["minigame_id"] == "mg-wardens-onslaught"
    assert payload["minigame_type"] == "dodge"
    assert payload["dodge_config"] == {"difficulty": 3}

    updated = await _load_playthrough(db_session, playthrough.playthrough_id)
    assert updated.state["_pending_minigame"]["minigame_id"] == "mg-wardens-onslaught"
    assert updated.status == "active"


async def test_lockpick_minigame_event_carries_lockpick_config(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_narration("The lock clicks."),
    )
    records_cage_lock = {
        **_WARDENS_ONSLAUGHT,
        "minigame_id": "mg-records-cage",
        "minigame_type": "lockpick",
        "label": "Records Cage",
        "dodge_config": None,
        "lockpick_config": {"version": 1, "difficulty": 4, "picks": 2},
    }
    playthrough, participant = await _seed_master_playthrough(
        db_session, [records_cage_lock]
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I kneel at the cage lock.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    payload = json.loads(next(e for e in events if e.event == "minigame").data)
    assert payload["lockpick_config"] == {"version": 1, "difficulty": 4, "picks": 2}


_COMPOSURE_CONFIG = {
    "version": 1,
    "target_bpm": 44,
    "beats_to_win": 6,
    "tolerance_ms": 200,
    "max_strikes": 3,
    "keys": ["W", "S"],
    "audio_profile": "chase",
    "texts": {
        "instructions": "Hum.",
        "start_text": "Begin",
        "win_text": "Calm.",
        "lose_text": "Broken.",
    },
}


async def test_composure_config_survives_the_hop_and_no_mutation_key_leaks(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_narration("The stairwell hums."),
    )
    stairwell = {
        **_WARDENS_ONSLAUGHT,
        "minigame_id": "mg-stairwell",
        "minigame_type": "rhythm_composure",
        "label": "The stairwell hum",
        "dodge_config": None,
        "composure_config": _COMPOSURE_CONFIG,
        "win_mutations": [{"path": "player.health", "op": "increment", "value": 5}],
        "lose_mutations": [{"path": "player.health", "op": "decrement", "value": 20}],
    }
    playthrough, participant = await _seed_master_playthrough(db_session, [stairwell])

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I go down the stairs.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    raw = next(e for e in events if e.event == "minigame").data
    payload = json.loads(raw)
    assert payload["minigame_type"] == "rhythm_composure"
    assert payload["composure_config"] == _COMPOSURE_CONFIG
    for secret in ("win_mutation", "lose_mutation", "timeout_mutation", "narrator"):
        assert secret not in raw


async def test_composure_result_applies_its_mutation_list_like_any_minigame(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_narration("You steady your breath."),
    )
    stairwell = {
        **_WARDENS_ONSLAUGHT,
        "minigame_id": "mg-stairwell",
        "minigame_type": "rhythm_composure",
        "dodge_config": None,
        "composure_config": _COMPOSURE_CONFIG,
        "win_mutation": None,
        "lose_mutation": None,
        "win_mutations": [
            {"path": "flags.tactical_advantage", "op": "set", "value": True},
            {"path": "player.health", "op": "decrement", "value": 10},
        ],
        "lose_mutations": [{"path": "player.health", "op": "decrement", "value": 20}],
    }
    playthrough, participant = await _seed_master_playthrough(
        db_session,
        [stairwell],
        state_overrides={
            "_pending_minigame": {
                "minigame_id": "mg-stairwell",
                "attempt_id": "attempt-1",
                "minigame_type": "rhythm_composure",
            }
        },
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="(composure)",
        action_kind="minigame_result",
        minigame_result={
            "minigame_id": "mg-stairwell",
            "outcome_tag": "win",
            "score": 6,
            "attempt_id": "attempt-1",
        },
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    [event async for event in response.body_iterator]

    updated = await _load_playthrough(db_session, playthrough.playthrough_id)
    assert updated.state["flags"]["tactical_advantage"] is True
    assert updated.state["player"]["health"] == 90


async def test_minigame_event_payload_never_leaks_mutation_or_instruction_fields(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_narration("The Warden falls."),
    )
    playthrough, participant = await _seed_master_playthrough(
        db_session, [_WARDENS_ONSLAUGHT]
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I strike.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    minigame_event = next(e for e in events if e.event == "minigame")
    for forbidden in (
        "win_mutation",
        "lose_mutation",
        "tiered_outcomes",
        "timeout_mutation",
        "narrator_instruction_template",
    ):
        assert forbidden not in minigame_event.data


async def test_solo_only_gate_suppresses_trigger_in_multiplayer(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_narration("The Warden falls."),
    )
    playthrough, participant_one = await _seed_master_playthrough(
        db_session, [_WARDENS_ONSLAUGHT]
    )
    await _add_second_participant(db_session, playthrough.playthrough_id)

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant_one.participant_id,
        action_text="I strike.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant_one.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    assert "minigame" not in [e.event for e in events]
    updated = await _load_playthrough(db_session, playthrough.playthrough_id)
    assert "_pending_minigame" not in updated.state


async def test_end_condition_suppressed_when_minigame_triggers_same_turn(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_narration("The Warden falls."),
    )
    call_count = {"n": 0}
    original = end_condition_evaluator.evaluate_end_conditions

    def _counting_spy(*args, **kwargs):
        call_count["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        end_condition_evaluator, "evaluate_end_conditions", _counting_spy
    )

    playthrough, participant = await _seed_master_playthrough(
        db_session,
        [_WARDENS_ONSLAUGHT],
        end_conditions=[_WARDEN_DEFEATED_END_CONDITION],
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I strike the final blow.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    assert call_count["n"] == 0
    assert "minigame" in [e.event for e in events]
    assert "playthrough_ended" not in [e.event for e in events]

    updated = await _load_playthrough(db_session, playthrough.playthrough_id)
    assert updated.status == "active"


async def test_pending_minigame_rejects_normal_action(
    db_session: AsyncSession,
) -> None:
    playthrough, participant = await _seed_master_playthrough(
        db_session,
        [_WARDENS_ONSLAUGHT],
        state_overrides={
            "_pending_minigame": {
                "minigame_id": "mg-wardens-onslaught",
                "minigame_type": "dodge",
            }
        },
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I try to just keep walking.",
    )

    with pytest.raises(MinigameResultRequiredError):
        await pipeline.run_turn(
            turn_input,
            await committed_factory(db_session),
            CurrentUser(user_id=participant.user_id, token_version=1),
        )


async def test_mismatched_minigame_result_is_rejected(
    db_session: AsyncSession,
) -> None:
    playthrough, participant = await _seed_master_playthrough(
        db_session,
        [_WARDENS_ONSLAUGHT],
        state_overrides={
            "_pending_minigame": {
                "minigame_id": "mg-wardens-onslaught",
                "minigame_type": "dodge",
            }
        },
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="",
        action_kind="minigame_result",
        minigame_result={"minigame_id": "wrong-id", "outcome_tag": "win"},
    )

    with pytest.raises(MinigameResultMismatchError):
        await pipeline.run_turn(
            turn_input,
            await committed_factory(db_session),
            CurrentUser(user_id=participant.user_id, token_version=1),
        )


async def test_minigame_result_submission_with_nothing_pending_is_rejected(
    db_session: AsyncSession,
) -> None:
    playthrough, participant = await _seed_master_playthrough(
        db_session, [_WARDENS_ONSLAUGHT]
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="",
        action_kind="minigame_result",
        minigame_result={"minigame_id": "mg-wardens-onslaught", "outcome_tag": "win"},
    )

    with pytest.raises(MinigameResultMismatchError):
        await pipeline.run_turn(
            turn_input,
            await committed_factory(db_session),
            CurrentUser(user_id=participant.user_id, token_version=1),
        )


async def test_minigame_result_resolution_applies_mutation_and_clears_pending(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_narration("You feel the tactical advantage settle in."),
    )
    # win_mutation also raises the_warden.health above 0, so the same
    # minigame's trigger_condition_expression ("the_warden.health <= 0")
    # no longer matches on the resolution turn itself.
    resolved_minigame = {
        **_WARDENS_ONSLAUGHT,
        "win_mutation": {"path": "the_warden.health", "op": "set", "value": 50},
    }
    playthrough, participant = await _seed_master_playthrough(
        db_session,
        [resolved_minigame],
        state_overrides={
            "_pending_minigame": {
                "minigame_id": "mg-wardens-onslaught",
                "minigame_type": "dodge",
            }
        },
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="",
        action_kind="minigame_result",
        minigame_result={"minigame_id": "mg-wardens-onslaught", "outcome_tag": "win"},
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    assert "minigame" not in [e.event for e in events]

    updated = await _load_playthrough(db_session, playthrough.playthrough_id)
    assert "_pending_minigame" not in updated.state
    assert updated.state["the_warden"]["health"] == 50.0
