"""state_update: sent before narration, only for HUD/rule-sheet scenarios, never replayed."""

import json
import uuid

import pytest
from app.turn.steps import ai_orchestrator
from pipeline_seed import narrator, seed_master_playthrough, take_turn
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _snapshot(tools: list[str]) -> dict:
    return {
        "mode": "master",
        "enabled_tools": tools,
        "narrator_persona": "Dry.",
        "world_data": {},
        "state_schema": {
            "clock": {"type": "number"},
            "sanity": {"type": "number", "min": -100, "max": 100},
            "dread": {"type": "number", "hidden": True},
        },
        "entities": [],
        "rule_invariants": [],
        "end_conditions": [],
        "scenario_minigames": [],
        "scenario_conditions": [
            {
                "condition_id": "drain",
                "label": "The building drains you",
                "condition_expression": {"field": "clock", "op": ">=", "value": 5},
                "narrator_instruction": "The air is heavy.",
                "state_mutations": [{"path": "sanity", "op": "decrement", "value": 20}],
                "sensory_cue": "phone_ring",
            }
        ],
    }


async def _seed(session: AsyncSession, tools: list[str]):
    return await seed_master_playthrough(
        session,
        _snapshot(tools),
        {"clock": 6, "sanity": 80, "dread": 3, "narrative": {}},
    )


def _names(events) -> list[str]:
    return [event.event for event in events]


async def test_state_update_arrives_after_the_cue_and_before_narration(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        narrator("The air thins."),
    )
    playthrough, participant = await _seed(db_session, ["status_hud", "atmosphere"])

    events = await take_turn(db_session, playthrough, participant)

    names = _names(events)
    assert names.index("sensory_cue") < names.index("state_update")
    assert names.index("state_update") < names.index("narration")
    assert names.count("state_update") == 1


async def test_state_update_carries_post_intake_values_and_hides_hidden_fields(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        narrator("The air thins."),
    )
    playthrough, participant = await _seed(db_session, ["status_hud"])

    events = await take_turn(db_session, playthrough, participant)

    payload = json.loads(next(e for e in events if e.event == "state_update").data)
    assert payload["state"]["sanity"] == 60
    assert payload["state"]["clock"] == 6
    assert "dread" not in payload["state"]
    assert "rule_sheet" not in payload
    assert "_active_conditions" in payload["state"]


async def test_no_state_update_without_a_hud_tool(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        narrator("The air thins."),
    )
    playthrough, participant = await _seed(db_session, [])

    events = await take_turn(db_session, playthrough, participant)

    assert "state_update" not in _names(events)
    assert "sensory_cue" not in _names(events)


async def test_state_update_is_not_replayed_on_retry(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        narrator("The air thins."),
    )
    playthrough, participant = await _seed(db_session, ["status_hud"])
    client_action_id = uuid.uuid4()

    first = await take_turn(
        db_session, playthrough, participant, client_action_id=client_action_id
    )
    replay = await take_turn(
        db_session, playthrough, participant, client_action_id=client_action_id
    )

    assert "state_update" in _names(first)
    assert "state_update" not in _names(replay)


async def test_no_tools_event_sequence_is_unchanged(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        narrator("The air thins."),
    )
    playthrough, participant = await _seed(db_session, [])

    events = await take_turn(db_session, playthrough, participant)

    assert _names(events) == ["narration", "turn_summary", "done"]
