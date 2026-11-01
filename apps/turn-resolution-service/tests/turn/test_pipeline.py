"""Integration test running the full turn pipeline against a real test Postgres."""

import json
import uuid
from unittest.mock import AsyncMock

import pytest
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from app.db.models.user import User
from app.exceptions.memory_exceptions import MemoryRetrieveError
from app.exceptions.turn_exceptions import (
    OptimisticLockError,
    StateWriteError,
)
from app.integrations import memory_client
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.session import notification_manager, spectator_manager
from app.turn import pipeline
from app.turn.steps import ai_orchestrator
from google.genai import types
from session_factories import committed_factory
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_playthrough(session: AsyncSession) -> tuple[Playthrough, Participant]:
    # IDs generated explicitly: the ORM column's default=uuid.uuid4 only fires
    # at flush/INSERT time, not at object construction.
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    user = User(
        user_id=user_id, display_name="Tester", auth_provider_id=str(uuid.uuid4())
    )
    scenario = Scenario(
        scenario_id=scenario_id,
        creator_id=user_id,
        title="Test Scenario",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
    )
    playthrough = Playthrough(
        scenario_id=scenario_id,
        created_by=user_id,
        scenario_version=1,
        scenario_snapshot={
            "narrator_persona": "A grim voice.",
            "world_data": "A dungeon.",
        },
        state={"setup": {}, "narrative": {"opening_prompt": None}},
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


async def test_run_turn_streams_narration_and_persists_turn(
    db_session: AsyncSession, monkeypatch
) -> None:
    async def fake_stream(system_instruction: str, prompt: str, timeout_seconds: int):
        yield "You step into "
        yield "the torchlit corridor."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )

    playthrough, participant = await _seed_playthrough(db_session)

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I step forward.",
    )

    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    event_types = [event.event for event in events]
    assert event_types == ["narration", "done"]

    turn_log_stmt = select(TurnLog).where(
        TurnLog.playthrough_id == playthrough.playthrough_id
    )
    turn_log = (await db_session.execute(turn_log_stmt)).scalars().first()
    assert turn_log is not None
    assert turn_log.narration_text == "You step into the torchlit corridor."
    assert turn_log.action_text == "I step forward."

    playthrough_stmt = (
        select(Playthrough)
        .execution_options(populate_existing=True)
        .where(Playthrough.playthrough_id == playthrough.playthrough_id)
    )
    updated = (await db_session.execute(playthrough_stmt)).scalars().first()
    assert updated is not None
    assert updated.turn_count == 1
    assert "turns_so_far" not in updated.state["narrative"]
    assert turn_log.client_action_id == turn_input.client_action_id


async def test_run_turn_degrades_gracefully_on_write_failure(
    db_session: AsyncSession, monkeypatch
) -> None:
    async def fake_stream(system_instruction: str, prompt: str, timeout_seconds: int):
        yield "Narration before the failure."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )

    playthrough, participant = await _seed_playthrough(db_session)

    monkeypatch.setattr(
        pipeline.state_writer, "write_turn", AsyncMock(side_effect=StateWriteError())
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I step forward.",
    )

    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    event_types = [event.event for event in events]
    assert event_types == ["narration", "degraded"]

    turn_log_stmt = select(TurnLog).where(
        TurnLog.playthrough_id == playthrough.playthrough_id
    )
    turn_log = (await db_session.execute(turn_log_stmt)).scalars().first()
    assert turn_log is None


async def test_run_turn_degrades_on_optimistic_lock_collision(
    db_session: AsyncSession, monkeypatch
) -> None:
    async def fake_stream(system_instruction: str, prompt: str, timeout_seconds: int):
        yield "Narration before collision."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )
    playthrough, participant = await _seed_playthrough(db_session)
    monkeypatch.setattr(
        pipeline.state_writer,
        "write_turn",
        AsyncMock(side_effect=OptimisticLockError()),
    )

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I step forward.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]
    assert [event.event for event in events] == ["narration", "degraded"]
    degraded = next(event for event in events if event.event == "degraded")
    assert degraded.data == pipeline._DEGRADED_CONCURRENCY_MESSAGE


async def test_run_turn_notifies_next_participant_in_multiplayer(
    db_session: AsyncSession, monkeypatch
) -> None:
    async def fake_stream(system_instruction: str, prompt: str, timeout_seconds: int):
        yield "The other adventurer watches."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )

    playthrough, participant_one = await _seed_playthrough(db_session)
    second_user_id = uuid.uuid4()
    db_session.add(
        User(
            user_id=second_user_id,
            display_name="Second Tester",
            auth_provider_id=str(uuid.uuid4()),
        )
    )
    await db_session.flush()
    participant_two = Participant(
        playthrough_id=playthrough.playthrough_id,
        user_id=second_user_id,
        role="joined",
        turn_order_position=2,
    )
    db_session.add(participant_two)
    await db_session.flush()

    queue = notification_manager.subscribe(
        playthrough.playthrough_id, participant_two.participant_id
    )
    try:
        turn_input = TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=playthrough.playthrough_id,
            participant_id=participant_one.participant_id,
            action_text="I step forward.",
        )
        response = await pipeline.run_turn(
            turn_input,
            await committed_factory(db_session),
            CurrentUser(user_id=participant_one.user_id, token_version=1),
        )
        [event async for event in response.body_iterator]

        assert not queue.empty()
        event_name, _ = queue.get_nowait()
        assert event_name == "your_turn"
    finally:
        notification_manager.unsubscribe(
            playthrough.playthrough_id, participant_two.participant_id, queue
        )


# --- Master mode end-to-end: "The Hollow Cairn" fixture ---------------------


class _FakeCandidate:
    def __init__(self) -> None:
        self.content = "fake-model-turn-content"


class _FakeResponse:
    def __init__(self, function_calls: list[types.FunctionCall], text: str) -> None:
        self.function_calls = function_calls
        self.text = text
        self.candidates = [_FakeCandidate()]


async def _seed_master_playthrough(
    session: AsyncSession,
) -> tuple[Playthrough, Participant]:
    """A minimal slice of "The Hollow Cairn": one entity, one invariant, one
    Effect C active condition, and a state_schema with a player.sanity field."""
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    warden_id = str(uuid.uuid4())
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
                    "fields": {
                        "health": {
                            "type": "number",
                            "min": 0,
                            "max": 100,
                            "initial": 100,
                        },
                        "sanity": {
                            "type": "number",
                            "min": 0,
                            "max": 100,
                            "initial": 100,
                        },
                    },
                },
                "flags": {
                    "type": "object",
                    "fields": {"entered_cairn": {"type": "boolean", "initial": False}},
                },
            },
            "entities": [
                {
                    "entity_id": warden_id,
                    "attributes_schema": {
                        "health": {
                            "type": "number",
                            "min": 0,
                            "max": 150,
                            "initial": 150,
                        }
                    },
                    "narrator_instruction": "The Warden speaks rarely.",
                }
            ],
            "rule_invariants": [
                {
                    "label": "Health cap",
                    "invariant_expression": {
                        "field": "player.health",
                        "op": "<=",
                        "value": 100,
                    },
                    "narrator_text": "Health cannot exceed its cap.",
                }
            ],
            "scenario_conditions": [
                {
                    "label": "The Cairn Presses In",
                    "condition_expression": {
                        "field": "flags.entered_cairn",
                        "op": "==",
                        "value": True,
                    },
                    "narrator_instruction": "The cairn presses in on the player's mind.",
                    "state_mutation": {
                        "path": "player.sanity",
                        "op": "decrement",
                        "value": 2,
                    },
                }
            ],
        },
        state={
            "player": {"health": 100, "sanity": 100},
            "flags": {"entered_cairn": True},
            "narrative": {},
        },
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


async def test_run_turn_master_mode_end_to_end(
    db_session: AsyncSession, monkeypatch
) -> None:
    """Effect C fires pre-turn, a validated tool call mutates state, and both
    reach Playthrough.state/TurnLog by the time the turn completes — all in
    one streamed call, no round trip (the function-call chunk carries no
    text, matching Gemini's actual streaming shape; narration follows in a
    separate chunk)."""

    async def fake_stream_with_tools(
        system_instruction, contents, timeout_seconds, tools
    ):
        yield _FakeResponse(
            [
                types.FunctionCall(
                    name="adjust_numeric_field",
                    args={"path": "player.health", "delta": -15},
                )
            ],
            None,
        )
        yield _FakeResponse(
            [], "The cairn watches as you step forward, health failing."
        )

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", fake_stream_with_tools
    )

    playthrough, participant = await _seed_master_playthrough(db_session)

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I step into the cairn.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    # turn_summary is emitted after narration finishes, before done, so the
    # frontend can defer showing it until that turn's narration is done
    # streaming (see response_streamer.turn_summary_event's docstring).
    assert [e.event for e in events] == [
        "narration",
        "turn_summary",
        "done",
    ]

    summary = json.loads(next(e.data for e in events if e.event == "turn_summary"))
    assert summary["active_conditions"] == ["The Cairn Presses In"]
    assert summary["stat_changes"] == [
        {
            "path": "player.health",
            "label": "Health",
            "before": 100,
            "after": 85,
            "delta": -15.0,
        }
    ]
    assert summary["inventory_changes"] == []

    turn_log_stmt = select(TurnLog).where(
        TurnLog.playthrough_id == playthrough.playthrough_id
    )
    turn_log = (await db_session.execute(turn_log_stmt)).scalars().first()
    assert turn_log is not None
    assert len(turn_log.tool_calls) == 1
    assert turn_log.tool_calls[0]["tool_name"] == "adjust_numeric_field"

    playthrough_stmt = (
        select(Playthrough)
        .execution_options(populate_existing=True)
        .where(Playthrough.playthrough_id == playthrough.playthrough_id)
    )
    updated = (await db_session.execute(playthrough_stmt)).scalars().first()
    assert updated is not None
    # Effect C: sanity 100 -> 98. AI tool call: health 100 -> 85.
    assert updated.state["player"]["sanity"] == 98.0
    assert updated.state["player"]["health"] == 85.0
    assert updated.state["_last_changed_fields"] == sorted(
        ["player.sanity", "player.health"]
    )


async def test_run_turn_master_mode_effect_c_precedes_narration_call(
    db_session: AsyncSession, monkeypatch
) -> None:
    """Effect C's condition_evaluator mutation must complete — and be visible
    to the AI — strictly before the first (and only) Gemini call of the turn."""
    call_order: list[str] = []

    original_evaluate = pipeline.condition_evaluator.evaluate_conditions

    def spy_evaluate_conditions(loaded_state):
        call_order.append("condition_evaluator")
        return original_evaluate(loaded_state)

    monkeypatch.setattr(
        pipeline.condition_evaluator, "evaluate_conditions", spy_evaluate_conditions
    )

    async def fake_stream_with_tools(
        system_instruction, contents, timeout_seconds, tools
    ):
        call_order.append("gemini_call")
        yield _FakeResponse([], "The cairn watches.")

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", fake_stream_with_tools
    )

    playthrough, participant = await _seed_master_playthrough(db_session)
    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I step into the cairn.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    [event async for event in response.body_iterator]

    assert call_order == ["condition_evaluator", "gemini_call"]

    playthrough_stmt = (
        select(Playthrough)
        .execution_options(populate_existing=True)
        .where(Playthrough.playthrough_id == playthrough.playthrough_id)
    )
    updated = (await db_session.execute(playthrough_stmt)).scalars().first()
    assert updated.state["player"]["sanity"] == 98.0  # Effect C's mutation persisted


async def test_run_turn_master_mode_rejects_invariant_violating_mutation(
    db_session: AsyncSession, monkeypatch
) -> None:
    """A tool call that would push health above its invariant cap is
    rejected — logged as invalid, never applied. There is no round trip for
    the model to react to the rejection; the narration from this same call
    still streams (an accepted trade-off of the single-call turn, see
    ai_orchestrator._apply_function_calls's docstring)."""

    async def fake_stream_with_tools(
        system_instruction, contents, timeout_seconds, tools
    ):
        yield _FakeResponse(
            [
                types.FunctionCall(
                    name="set_field", args={"path": "player.health", "value": "500"}
                )
            ],
            None,
        )
        yield _FakeResponse([], "Nothing happens; the wound refuses to close.")

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", fake_stream_with_tools
    )

    playthrough, participant = await _seed_master_playthrough(db_session)

    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I try to overheal.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    [event async for event in response.body_iterator]

    playthrough_stmt = (
        select(Playthrough)
        .execution_options(populate_existing=True)
        .where(Playthrough.playthrough_id == playthrough.playthrough_id)
    )
    updated = (await db_session.execute(playthrough_stmt)).scalars().first()
    assert updated is not None
    assert updated.state["player"]["health"] == 100  # unchanged — rejected

    turn_log_stmt = select(TurnLog).where(
        TurnLog.playthrough_id == playthrough.playthrough_id
    )
    turn_log = (await db_session.execute(turn_log_stmt)).scalars().first()
    assert turn_log.tool_calls[0]["is_valid"] is False


async def test_run_turn_streams_mood_event_and_relays_to_spectator(
    db_session: AsyncSession, monkeypatch
) -> None:
    async def fake_stream(system_instruction: str, prompt: str, timeout_seconds: int):
        yield "[MOOD: combat]\n"
        yield "An ambush strikes from the dark!"

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )

    playthrough, participant = await _seed_playthrough(db_session)
    spectator_queue = spectator_manager.subscribe(playthrough.playthrough_id)

    try:
        turn_input = TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=playthrough.playthrough_id,
            participant_id=participant.participant_id,
            action_text="I enter the shadows.",
        )
        response = await pipeline.run_turn(
            turn_input,
            await committed_factory(db_session),
            CurrentUser(user_id=participant.user_id, token_version=1),
        )
        events = [event async for event in response.body_iterator]

        event_types = [event.event for event in events]
        assert event_types == ["mood", "narration", "done"]
        assert events[0].data == "combat"
        assert events[1].data == "An ambush strikes from the dark!"

        spectator_events = []
        while not spectator_queue.empty():
            spectator_events.append(spectator_queue.get_nowait())

        assert ("mood", "combat") in spectator_events
        assert ("narration", "An ambush strikes from the dark!") in spectator_events
    finally:
        spectator_manager.unsubscribe(playthrough.playthrough_id, spectator_queue)


async def test_run_turn_succeeds_when_memory_retrieve_fails(
    db_session: AsyncSession, monkeypatch
) -> None:
    async def fake_retrieve(request):
        raise MemoryRetrieveError("unavailable")

    monkeypatch.setattr(memory_client, "retrieve", fake_retrieve)

    async def fake_stream(system_instruction: str, prompt: str, timeout_seconds: int):
        yield "The story continues despite memory failure."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )

    playthrough, participant = await _seed_playthrough(db_session)
    playthrough.memory_publish_revision = 1
    await db_session.flush()
    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I push forward into the mist.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]

    event_types = [event.event for event in events]
    assert "narration" in event_types
    assert "done" in event_types
    narration_event = next(e for e in events if e.event == "narration")
    assert narration_event.data == "The story continues despite memory failure."

    await db_session.refresh(playthrough)
    assert playthrough.turn_count == 1


async def test_run_turn_persists_token_usage_in_turn_log(
    db_session: AsyncSession, monkeypatch
) -> None:
    async def fake_stream_with_usage(
        system_instruction: str, prompt: str, timeout_seconds: int, usage_sink=None
    ):
        if usage_sink:
            usage_sink.prompt_tokens = 142
            usage_sink.completion_tokens = 38
            usage_sink.model_name = "gemini-2.5-flash"
        yield "You discover an ancient rune."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream_with_usage
    )

    playthrough, participant = await _seed_playthrough(db_session)
    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I examine the ancient wall.",
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    events = [event async for event in response.body_iterator]
    assert any(e.event == "done" for e in events)

    stmt = select(TurnLog).where(TurnLog.playthrough_id == playthrough.playthrough_id)
    turn_log = (await db_session.execute(stmt)).scalars().first()
    assert turn_log is not None
    assert turn_log.prompt_tokens == 142
    assert turn_log.completion_tokens == 38
    assert turn_log.model_name == "gemini-2.5-flash"
