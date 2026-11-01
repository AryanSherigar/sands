"""sensory_cue events: rising edge, before narration, atmosphere-gated, no replay."""

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
        "state_schema": {"clock": {"type": "number"}},
        "entities": [],
        "rule_invariants": [],
        "end_conditions": [],
        "scenario_minigames": [],
        "scenario_conditions": [
            {
                "condition_id": "phone",
                "label": "The 03:14 phone",
                "condition_expression": {"field": "clock", "op": ">=", "value": 5},
                "narrator_instruction": "The phone rings in the dark.",
                "sensory_cue": "phone_ring",
                "cut_ambient": True,
                "silence_duration_ms": 1500,
            }
        ],
    }


async def _seed(session: AsyncSession, tools: list[str]):
    return await seed_master_playthrough(
        session, _snapshot(tools), {"clock": 6, "narrative": {}}
    )


async def test_cue_is_sent_before_the_first_narration_token(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("It rings.")
    )
    playthrough, participant = await _seed(db_session, ["atmosphere", "status_hud"])

    events = await take_turn(db_session, playthrough, participant)

    names = [e.event for e in events]
    assert names.index("sensory_cue") < names.index("narration")
    cue = json.loads(next(e for e in events if e.event == "sensory_cue").data)
    assert cue == {
        "cue": "phone_ring",
        "cut_ambient": True,
        "silence_duration_ms": 1500,
    }


async def test_cue_comes_after_check_resolved_when_both_happen(
    db_session: AsyncSession, monkeypatch
) -> None:
    from test_pipeline_rule_checks import DEFINITION_ID, SNAPSHOT

    snapshot = {
        **SNAPSHOT,
        "enabled_tools": ["rule_checks", "atmosphere", "status_hud"],
        "scenario_conditions": [
            {
                "condition_id": "after",
                "label": "After answering",
                "condition_expression": {"field": "clock", "op": ">=", "value": 5},
                "narrator_instruction": "The line crackles.",
                "sensory_cue": "radio_static",
            }
        ],
    }
    state = {
        "clock": 6,
        "alarm": False,
        "rules": {"r3": "unseen"},
        "narrative": {},
        "_check_edges": [DEFINITION_ID],
    }
    playthrough, participant = await seed_master_playthrough(
        db_session, snapshot, state
    )
    playthrough.state = {
        **state,
        "_pending_check": {
            "check_id": "chk-1",
            "kind": "timed_choice",
            "check_def_id": DEFINITION_ID,
            "prompt": "The phone rings.",
            "options": [{"id": "answer", "label": "Answer it"}],
            "window_ms": 12000,
            "issued_at": 9_999_999_999_999,
            "resolved": None,
        },
    }
    await db_session.flush()
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("Static.")
    )

    events = await take_turn(
        db_session,
        playthrough,
        participant,
        action_kind="check_report",
        action_text="(answers)",
        check_report={"check_id": "chk-1", "choice_id": "answer"},
    )

    names = [e.event for e in events]
    assert names.index("check_resolved") < names.index("sensory_cue")
    assert names.index("sensory_cue") < names.index("narration")


async def test_no_cue_event_without_the_atmosphere_tool(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("It rings.")
    )
    playthrough, participant = await _seed(db_session, [])

    events = await take_turn(db_session, playthrough, participant)

    assert "sensory_cue" not in [e.event for e in events]


async def test_cue_is_not_replayed_when_the_turn_is_retried(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("It rings.")
    )
    playthrough, participant = await _seed(db_session, ["atmosphere", "status_hud"])
    client_action_id = uuid.uuid4()

    first = await take_turn(
        db_session, playthrough, participant, client_action_id=client_action_id
    )
    replay = await take_turn(
        db_session, playthrough, participant, client_action_id=client_action_id
    )

    assert "sensory_cue" in [e.event for e in first]
    assert "sensory_cue" not in [e.event for e in replay]
    assert "narration" in [e.event for e in replay]
