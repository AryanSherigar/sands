"""flag_rule_violation: the tool declaration and how a call is applied."""

import pytest
from app.models.tool_call import MasterModeTurnResult
from app.turn import tool_definitions
from app.turn.rule_violation import apply_rule_violation
from google.genai import types

SNAPSHOT = {
    "enabled_tools": ["rule_sheet"],
    "state_schema": {
        "sanity": {"type": "number", "min": 0, "max": 100},
        "rule_status": {
            "type": "object",
            "hidden": True,
            "fields": {
                "r1": {"type": "enum", "options": ["intact", "violated"]},
                "r2": {"type": "enum", "options": ["intact", "violated"]},
            },
        },
        "rule_flags": {
            "type": "object",
            "hidden": True,
            "fields": {"r2": {"type": "boolean"}},
        },
    },
    "sheet_rules": [
        {"key": "r1", "is_ai_flaggable": False},
        {"key": "r2", "is_ai_flaggable": True},
    ],
}


def _call(rule_id: str, evidence: str = "He opened the cage.") -> types.FunctionCall:
    return types.FunctionCall(
        name="flag_rule_violation", args={"rule_id": rule_id, "evidence": evidence}
    )


def _state() -> dict:
    return {
        "sanity": 80,
        "rule_status": {"r1": "intact", "r2": "intact"},
        "rule_flags": {"r2": False},
    }


def _names(tool: types.Tool) -> list[str]:
    return [declaration.name for declaration in tool.function_declarations]


def test_tool_is_absent_without_the_rule_sheet_tool() -> None:
    snapshot = {**SNAPSHOT, "enabled_tools": []}

    tool = tool_definitions.build_master_mode_tools(snapshot)

    assert tool is tool_definitions.MASTER_MODE_TOOLS
    assert "flag_rule_violation" not in _names(tool)


def test_tool_is_absent_when_no_rule_is_flaggable() -> None:
    snapshot = {**SNAPSHOT, "sheet_rules": [{"key": "r1", "is_ai_flaggable": False}]}

    assert "flag_rule_violation" not in _names(
        tool_definitions.build_master_mode_tools(snapshot)
    )


def test_tool_is_added_with_an_enum_of_exactly_the_flaggable_keys() -> None:
    tool = tool_definitions.build_master_mode_tools(SNAPSHOT)

    declaration = next(
        d for d in tool.function_declarations if d.name == "flag_rule_violation"
    )
    rule_id = declaration.parameters.properties["rule_id"]
    assert rule_id.enum == ["r2"]
    assert declaration.parameters.required == ["rule_id", "evidence"]
    assert set(_names(tool)) >= {"set_field", "propose_check", "flag_rule_violation"}


def test_the_static_tool_set_is_not_mutated_by_building_a_richer_one() -> None:
    before = _names(tool_definitions.MASTER_MODE_TOOLS)

    tool_definitions.build_master_mode_tools(SNAPSHOT)

    assert _names(tool_definitions.MASTER_MODE_TOOLS) == before


def test_a_valid_call_raises_the_flag_and_logs_the_evidence() -> None:
    sink = MasterModeTurnResult(final_state=_state())

    state = apply_rule_violation(_call("r2"), _state(), SNAPSHOT, sink)

    assert state["rule_flags"]["r2"] is True
    assert state["rule_status"]["r2"] == "intact"
    entry = sink.tool_calls[0]
    assert entry.is_valid is True
    assert entry.arguments["evidence"] == "He opened the cage."
    assert entry.arguments["path"] == "rule_flags.r2"
    assert sink.mutated_paths == ["rule_flags.r2"]


def test_an_unflaggable_rule_is_rejected_without_a_state_change() -> None:
    sink = MasterModeTurnResult(final_state=_state())

    state = apply_rule_violation(_call("r1"), _state(), SNAPSHOT, sink)

    assert state == _state()
    assert sink.tool_calls[0].is_valid is False
    assert sink.mutated_paths == []


def test_an_unknown_rule_is_rejected() -> None:
    sink = MasterModeTurnResult(final_state=_state())

    state = apply_rule_violation(_call("r99"), _state(), SNAPSHOT, sink)

    assert state == _state()
    assert sink.tool_calls[0].is_valid is False


def test_repeat_calls_for_one_rule_collapse_to_one_flag() -> None:
    sink = MasterModeTurnResult(final_state=_state())

    first = apply_rule_violation(_call("r2"), _state(), SNAPSHOT, sink)
    second = apply_rule_violation(_call("r2"), first, SNAPSHOT, sink)

    assert second["rule_flags"]["r2"] is True
    assert sink.mutated_paths == ["rule_flags.r2"]
    assert sink.tool_calls[1].result.get("collapsed") is True


def test_evidence_is_cut_to_the_limit() -> None:
    sink = MasterModeTurnResult(final_state=_state())

    apply_rule_violation(_call("r2", "x" * 500), _state(), SNAPSHOT, sink)

    assert len(sink.tool_calls[0].arguments["evidence"]) == 200


@pytest.mark.parametrize("rule_id", ["", "R2", "r2; drop"])
def test_malformed_ids_never_reach_state(rule_id: str) -> None:
    sink = MasterModeTurnResult(final_state=_state())

    state = apply_rule_violation(_call(rule_id), _state(), SNAPSHOT, sink)

    assert state == _state()
