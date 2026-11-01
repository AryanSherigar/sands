"""A scenario that opts in lets the narrator set intent fields with a final
marker line instead of a tool call (docs/adr/028-narrator-intent-marker.md)."""

import json

import pytest
from app.turn.steps import ai_orchestrator
from pipeline_seed import narrator, seed_master_playthrough, stored_state, take_turn
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")

NARRATION = "Ritsu thinks, then nods slowly."
MARKED_REPLY = (
    "[MOOD: peaceful]\n"
    f"[NARRATOR]\n{NARRATION}\n\n"
    "[INTENT: recruit_target=ritsu, time_cost=long, adopt_policy=not_a_policy]"
)


def _snapshot(is_enabled: bool) -> dict:
    snapshot: dict = {
        "mode": "master",
        "enabled_tools": [],
        "narrator_persona": "Dry.",
        "world_data": {},
        "state_schema": {
            "intent": {
                "type": "object",
                "fields": {
                    "recruit_target": {
                        "type": "enum",
                        "options": ["", "ritsu", "rosell"],
                        "initial": "",
                    },
                    "time_cost": {
                        "type": "enum",
                        "options": ["", "short", "long"],
                        "initial": "",
                    },
                    "adopt_policy": {
                        "type": "enum",
                        "options": ["", "tax_relief"],
                        "initial": "",
                    },
                },
            }
        },
        "entities": [],
        "rule_invariants": [],
        "end_conditions": [],
        "scenario_minigames": [],
        "scenario_conditions": [],
    }
    if is_enabled:
        snapshot["intent_marker_group"] = "intent"
    return snapshot


async def _play(session: AsyncSession, monkeypatch, is_enabled: bool):
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator(MARKED_REPLY)
    )
    state = {"intent": {"recruit_target": "", "time_cost": "", "adopt_policy": ""}}
    playthrough, participant = await seed_master_playthrough(
        session, _snapshot(is_enabled), {**state, "narrative": {}}
    )
    events = await take_turn(session, playthrough, participant)
    return events, await stored_state(session, playthrough)


def _shown(events) -> str:
    return "".join(e.data for e in events if e.event == "narration")


async def test_marker_sets_the_valid_fields_and_is_hidden(
    db_session: AsyncSession, monkeypatch
) -> None:
    events, state = await _play(db_session, monkeypatch, is_enabled=True)

    assert state["intent"]["recruit_target"] == "ritsu"
    assert state["intent"]["time_cost"] == "long"
    assert "INTENT" not in _shown(events)
    assert NARRATION in _shown(events)


async def test_a_value_outside_the_enum_is_rejected_by_normal_validation(
    db_session: AsyncSession, monkeypatch
) -> None:
    _, state = await _play(db_session, monkeypatch, is_enabled=True)

    assert state["intent"]["adopt_policy"] == ""


async def test_a_scenario_that_did_not_opt_in_ignores_the_marker(
    db_session: AsyncSession, monkeypatch
) -> None:
    events, state = await _play(db_session, monkeypatch, is_enabled=False)

    assert state["intent"]["recruit_target"] == ""
    assert "INTENT" in _shown(events)


async def test_the_turn_summary_does_not_leak_the_marker(
    db_session: AsyncSession, monkeypatch
) -> None:
    events, _ = await _play(db_session, monkeypatch, is_enabled=True)

    blob = json.dumps([e.data for e in events])
    assert "INTENT:" not in blob
