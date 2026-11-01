"""Phase 1 acceptance: the 03:14 phone, end to end through the real pipeline.

The clock reaches 03:14, so the phone cue plays and the clock updates before any
narration, the timed prompt opens, the player's answer is judged and written by
the server, and the answer changes the next turn's state.
"""

import json

import pytest
from app.turn.steps import ai_orchestrator
from pipeline_seed import narrator, seed_master_playthrough, stored_state, take_turn
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")

PHONE_CHECK_ID = "check-phone"
SNAPSHOT = {
    "mode": "master",
    "enabled_tools": ["rule_checks", "status_hud", "atmosphere"],
    "narrator_persona": "Dry.",
    "world_data": {},
    "state_schema": {
        "shift_minutes": {
            "type": "number",
            "initial": 0,
            "display": {
                "kind": "clock",
                "label": "Shift",
                "start": "23:00",
                "format": "12h",
            },
        },
        "sanity": {"type": "number", "min": -100, "max": 100, "initial": 85},
        "r3_phone": {
            "type": "enum",
            "options": ["answered", "ignored", "unseen"],
            "initial": "unseen",
            "hidden": True,
        },
    },
    "entities": [],
    "rule_invariants": [],
    "end_conditions": [],
    "scenario_minigames": [],
    "scenario_conditions": [
        {
            "condition_id": "phone-cue",
            "label": "03:14",
            "condition_expression": {
                "field": "shift_minutes",
                "op": ">=",
                "value": 254,
            },
            "narrator_instruction": "The desk phone starts to ring.",
            "sensory_cue": "phone_ring",
            "cut_ambient": True,
            "silence_duration_ms": 1200,
        },
        {
            "condition_id": "answered-consequence",
            "label": "Someone is on the line",
            "condition_expression": {
                "field": "r3_phone",
                "op": "==",
                "value": "answered",
            },
            "narrator_instruction": "Breathing on the line.",
            "state_mutations": [{"path": "sanity", "op": "decrement", "value": 30}],
            "is_one_shot": True,
        },
    ],
    "rule_checks": [
        {
            "check_id": PHONE_CHECK_ID,
            "label": "The 03:14 phone",
            "kind": "timed_choice",
            "trigger_condition_expression": {
                "field": "shift_minutes",
                "op": ">=",
                "value": 254,
            },
            "priority": 0,
            "result_path": "r3_phone",
            "params": {
                "prompt": "The desk phone is ringing. It is 03:14.",
                "options": [
                    {
                        "id": "answer",
                        "label": "Pick it up",
                        "result": "answered",
                        "mutations": [],
                    },
                    {
                        "id": "ignore",
                        "label": "Let it ring",
                        "result": "ignored",
                        "mutations": [],
                    },
                ],
                "window_ms": 12000,
                "timeout_result": "ignored",
            },
            "narrator_instruction_template": None,
        }
    ],
}


def _names(events) -> list[str]:
    return [event.event for event in events]


def _data(events, name: str) -> dict:
    return json.loads(next(e for e in events if e.event == name).data)


async def test_the_phone_rule_plays_end_to_end(
    db_session: AsyncSession, monkeypatch
) -> None:
    playthrough, participant = await seed_master_playthrough(
        db_session,
        SNAPSHOT,
        {"shift_minutes": 254, "sanity": 85, "r3_phone": "unseen", "narrative": {}},
    )
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("It rings.")
    )

    first = await take_turn(db_session, playthrough, participant)

    names = _names(first)
    assert (
        names.index("sensory_cue")
        < names.index("state_update")
        < names.index("narration")
    )
    assert _data(first, "sensory_cue")["cue"] == "phone_ring"
    assert _data(first, "state_update")["state"]["shift_minutes"] == 254
    assert "r3_phone" not in _data(first, "state_update")["state"]
    assert names.index("turn_summary") < names.index("check") < names.index("done")
    prompt = _data(first, "check")
    assert prompt["prompt"] == "The desk phone is ringing. It is 03:14."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("You lift it.")
    )
    answer = await take_turn(
        db_session,
        playthrough,
        participant,
        action_kind="check_report",
        action_text="Pick it up",
        check_report={"check_id": prompt["check_id"], "choice_id": "answer"},
    )

    answer_names = _names(answer)
    assert answer_names[0] == "check_resolved"
    assert answer_names.index("check_resolved") < answer_names.index("narration")
    after_answer = await stored_state(db_session, playthrough)
    assert after_answer["r3_phone"] == "answered"
    assert "_pending_check" not in after_answer

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("A breath.")
    )
    await take_turn(db_session, playthrough, participant)
    after_next_turn = await stored_state(db_session, playthrough)

    assert after_next_turn["sanity"] == 55
    assert after_next_turn["_fired_conditions"] == ["answered-consequence"]
