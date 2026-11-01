"""Rule sheet through the real pipeline: prompt block, state_update, violation tool."""

import json

import pytest
from app.turn.steps import ai_orchestrator
from google.genai import types
from pipeline_seed import (
    FakeCandidate,
    narrator,
    seed_master_playthrough,
    stored_state,
    take_turn,
)
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")

SHEET_RULES = [
    {
        "key": "r1",
        "number": 1,
        "text": "Never leave the desk before dawn.",
        "corrupted_text": None,
        "initial_status": "intact",
        "source_style": "typed",
        "is_ai_flaggable": False,
        "display_order": 0,
    },
    {
        "key": "r2",
        "number": 2,
        "text": "Never open the Records Cage.",
        "corrupted_text": None,
        "initial_status": "intact",
        "source_style": "typed",
        "is_ai_flaggable": True,
        "display_order": 1,
    },
    {
        "key": "r9",
        "number": 9,
        "text": "The thing behind the desk is not a rule.",
        "corrupted_text": None,
        "initial_status": "unrevealed",
        "source_style": "pencil",
        "is_ai_flaggable": False,
        "display_order": 2,
    },
]


def _snapshot(tools: list[str]) -> dict:
    return {
        "mode": "master",
        "enabled_tools": tools,
        "narrator_persona": "Dry.",
        "world_data": {},
        "state_schema": {
            "sanity": {"type": "number", "min": 0, "max": 100},
            "rule_status": {
                "type": "object",
                "hidden": True,
                "fields": {
                    key: {
                        "type": "enum",
                        "options": [
                            "unrevealed",
                            "intact",
                            "active_threat",
                            "violated",
                            "corrupted",
                        ],
                    }
                    for key in ("r1", "r2", "r9")
                },
            },
            "rule_flags": {
                "type": "object",
                "hidden": True,
                "fields": {"r2": {"type": "boolean"}},
            },
        },
        "sheet_rules": SHEET_RULES,
        "entities": [],
        "rule_invariants": [],
        "end_conditions": [],
        "scenario_minigames": [],
        "scenario_conditions": [
            {
                "condition_id": "r2-penalty",
                "label": "R2 broken",
                "condition_expression": {
                    "field": "rule_flags.r2",
                    "op": "==",
                    "value": True,
                },
                "narrator_instruction": "The cage breathes out.",
                "state_mutations": [
                    {"path": "sanity", "op": "decrement", "value": 30},
                    {"path": "rule_status.r2", "op": "set", "value": "violated"},
                    {"path": "rule_flags.r2", "op": "set", "value": False},
                ],
            }
        ],
    }


STATE = {
    "sanity": 80,
    "rule_status": {"r1": "intact", "r2": "intact", "r9": "unrevealed"},
    "rule_flags": {"r2": False},
    "narrative": {},
}


class _FlagResponse:
    def __init__(self, rule_id: str) -> None:
        self.function_calls = [
            types.FunctionCall(
                name="flag_rule_violation",
                args={"rule_id": rule_id, "evidence": "He opened the cage."},
            )
        ]
        self.text = None
        self.candidates = [FakeCandidate()]


class _TextResponse:
    def __init__(self, text: str) -> None:
        self.function_calls: list = []
        self.text = text
        self.candidates = [FakeCandidate()]


def _flagging_narrator(rule_id: str, tools_seen: list | None = None):
    async def _generate(system_instruction, contents, timeout_seconds, tools):
        if tools_seen is not None:
            tools_seen.append(tools)
        yield _FlagResponse(rule_id)
        yield _TextResponse("The cage door gives.")

    return _generate


async def _seed(session: AsyncSession, tools: list[str]):
    return await seed_master_playthrough(session, _snapshot(tools), dict(STATE))


async def test_prompt_lists_revealed_rules_only(
    db_session: AsyncSession, monkeypatch
) -> None:
    seen: list[str] = []
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        narrator("Quiet.", seen),
    )
    playthrough, participant = await _seed(db_session, ["rule_sheet"])

    await take_turn(db_session, playthrough, participant)

    prompt = seen[0]
    assert "## Rule Sheet" in prompt
    assert "Rule 1 [intact]: Never leave the desk before dawn." in prompt
    assert "Rule 2 [intact]: Never open the Records Cage." in prompt
    assert "not a rule" not in prompt
    assert "r9" not in prompt
    assert "rule_status" not in prompt


async def test_prompt_has_no_rule_sheet_block_when_the_tool_is_off(
    db_session: AsyncSession, monkeypatch
) -> None:
    seen: list[str] = []
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("Quiet.", seen)
    )
    playthrough, participant = await _seed(db_session, [])

    await take_turn(db_session, playthrough, participant)

    assert "## Rule Sheet" not in seen[0]


async def test_state_update_carries_the_revealed_sheet_and_no_raw_status(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("Quiet.")
    )
    playthrough, participant = await _seed(db_session, ["rule_sheet"])

    events = await take_turn(db_session, playthrough, participant)

    payload = json.loads(next(e for e in events if e.event == "state_update").data)
    assert [item["key"] for item in payload["rule_sheet"]] == ["r1", "r2"]
    assert "rule_status" not in payload["state"]
    assert "rule_flags" not in payload["state"]
    assert "not a rule" not in json.dumps(payload)


async def test_the_flag_tool_is_offered_and_a_flag_drives_the_penalty_next_turn(
    db_session: AsyncSession, monkeypatch
) -> None:
    tools_seen: list = []
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _flagging_narrator("r2", tools_seen),
    )
    playthrough, participant = await _seed(db_session, ["rule_sheet"])

    first = await take_turn(db_session, playthrough, participant)
    after_first = await stored_state(db_session, playthrough)
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("Quiet.")
    )
    await take_turn(db_session, playthrough, participant)
    after_second = await stored_state(db_session, playthrough)

    declared = [d.name for d in tools_seen[0][0].function_declarations]
    assert "flag_rule_violation" in declared
    assert after_first["rule_flags"]["r2"] is True
    assert after_first["sanity"] == 80
    assert after_second["sanity"] == 50
    assert after_second["rule_status"]["r2"] == "violated"
    assert after_second["rule_flags"]["r2"] is False
    summary = json.loads(next(e for e in first if e.event == "turn_summary").data)
    assert "r2" not in json.dumps(summary)


async def test_flagging_an_unflaggable_rule_changes_nothing(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _flagging_narrator("r1"),
    )
    playthrough, participant = await _seed(db_session, ["rule_sheet"])

    await take_turn(db_session, playthrough, participant)
    state = await stored_state(db_session, playthrough)

    assert state["rule_flags"] == {"r2": False}
    assert state["rule_status"]["r1"] == "intact"
