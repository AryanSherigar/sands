"""Pins today's behaviour: the narrator moving the player with set_field on
current_location_id makes a location-gated condition fire on the next turn."""

import uuid

import pytest
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.turn import pipeline
from app.turn.steps import ai_orchestrator
from google.genai import types
from session_factories import committed_factory
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")

LOBBY_ID = str(uuid.uuid4())
RECORDS_CAGE_ID = str(uuid.uuid4())


class _FakeCandidate:
    content = "fake-model-turn-content"


class _FakeResponse:
    def __init__(self, function_calls: list[types.FunctionCall], text: str) -> None:
        self.function_calls = function_calls
        self.text = text
        self.candidates = [_FakeCandidate()]


def _narrator(function_calls: list[types.FunctionCall], text: str):
    async def _generate(system_instruction, contents, timeout_seconds, tools):
        yield _FakeResponse(function_calls, None)
        yield _FakeResponse([], text)

    return _generate


def _location(entity_id: str, name: str) -> dict[str, object]:
    return {
        "entity_id": entity_id,
        "entity_type": "location",
        "canonical_name": name,
        "aliases": [],
        "description": None,
        "attributes_schema": {},
        "obtainable": None,
        "narrator_instruction": None,
        "is_player": False,
    }


async def _seed(session: AsyncSession) -> tuple[Playthrough, Participant]:
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    session.add(
        User(user_id=user_id, display_name="Tester", auth_provider_id=str(uuid.uuid4()))
    )
    await session.flush()
    session.add(
        Scenario(
            scenario_id=scenario_id,
            creator_id=user_id,
            title="Night Desk",
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
        scenario_snapshot={
            "mode": "master",
            "narrator_persona": "Dry.",
            "world_data": {},
            "state_schema": {
                "current_location_id": {
                    "type": "entity_ref",
                    "entity_type": "location",
                },
                "flags": {
                    "type": "object",
                    "fields": {"saw_the_cage": {"type": "boolean"}},
                },
            },
            "entities": [
                _location(LOBBY_ID, "Lobby"),
                _location(RECORDS_CAGE_ID, "Records Cage"),
            ],
            "rule_invariants": [],
            "end_conditions": [],
            "scenario_minigames": [],
            "scenario_conditions": [
                {
                    "condition_id": "in-cage",
                    "label": "In the cage",
                    "condition_expression": {
                        "field": "current_location_id",
                        "op": "==",
                        "value": RECORDS_CAGE_ID,
                    },
                    "narrator_instruction": "The cage smells of old paper.",
                    "state_mutation": {
                        "path": "flags.saw_the_cage",
                        "op": "set",
                        "value": True,
                    },
                }
            ],
        },
        state={
            "current_location_id": LOBBY_ID,
            "flags": {"saw_the_cage": False},
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


async def _take_turn(
    session: AsyncSession, playthrough: Playthrough, participant: Participant
) -> None:
    response = await pipeline.run_turn(
        TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=playthrough.playthrough_id,
            participant_id=participant.participant_id,
            action_text="I walk on.",
        ),
        await committed_factory(session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    [event async for event in response.body_iterator]


async def _stored_state(
    session: AsyncSession, playthrough: Playthrough
) -> dict[str, object]:
    stmt = (
        select(Playthrough)
        .execution_options(populate_existing=True)
        .where(Playthrough.playthrough_id == playthrough.playthrough_id)
    )
    stored = (await session.execute(stmt)).scalars().first()
    await session.refresh(stored)
    return stored.state


async def test_location_condition_fires_the_turn_after_the_narrator_moves_the_player(
    db_session: AsyncSession, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session)
    move = types.FunctionCall(
        name="set_field",
        args={"path": "current_location_id", "value": RECORDS_CAGE_ID},
    )
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _narrator([move], "You step into the cage."),
    )

    await _take_turn(db_session, playthrough, participant)
    after_move = await _stored_state(db_session, playthrough)

    assert after_move["current_location_id"] == RECORDS_CAGE_ID
    assert after_move["flags"]["saw_the_cage"] is False

    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _narrator([], "Paper dust drifts."),
    )
    await _take_turn(db_session, playthrough, participant)
    after_next_turn = await _stored_state(db_session, playthrough)

    assert after_next_turn["flags"]["saw_the_cage"] is True
