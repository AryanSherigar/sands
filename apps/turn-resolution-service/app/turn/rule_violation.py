"""Applies the narrator's `flag_rule_violation` call.

The model may only raise `rule_flags.<rule_id>` for a flaggable rule; the
scenario's own conditions turn that flag into a penalty and a `rule_status`
change. Every call is logged with its evidence for audit.
"""

from app.models.tool_call import (
    MasterModeTurnResult,
    ProposedMutation,
    ToolCallLogEntry,
)
from app.turn import tool_definitions
from app.turn.steps import state_validator
from google.genai import types

RULE_FLAGS_ROOT = "rule_flags"
ERROR_NOT_FLAGGABLE = "rule is not flaggable"


def apply_rule_violation(
    call: types.FunctionCall,
    working_state: dict[str, object],
    scenario_snapshot: dict[str, object],
    result_sink: MasterModeTurnResult | None,
) -> dict[str, object]:
    """Raise the flag for a flaggable rule. Repeat calls for one rule collapse to
    a single flag. The log entry carries the flag's path so hidden-field
    redaction drops it from anything the browser receives."""
    args = dict(call.args or {})
    rule_id = str(args.get("rule_id") or "")
    path = f"{RULE_FLAGS_ROOT}.{rule_id}"
    arguments = {
        "rule_id": rule_id,
        "evidence": str(args.get("evidence") or "")[
            : tool_definitions.EVIDENCE_MAX_LENGTH
        ],
        "path": path,
    }
    if rule_id not in tool_definitions.flaggable_rule_keys(scenario_snapshot):
        _log(result_sink, call, arguments, {"error": ERROR_NOT_FLAGGABLE}, False)
        return working_state
    if _is_flag_raised(working_state, rule_id):
        _log(result_sink, call, arguments, {"success": True, "collapsed": True}, True)
        return working_state
    return _raise_flag(call, working_state, scenario_snapshot, result_sink, arguments)


def _raise_flag(
    call: types.FunctionCall,
    working_state: dict[str, object],
    scenario_snapshot: dict[str, object],
    result_sink: MasterModeTurnResult | None,
    arguments: dict[str, object],
) -> dict[str, object]:
    path = str(arguments["path"])
    mutation = ProposedMutation(
        tool_name=call.name or "", op="set", path=path, value=True
    )
    validation = state_validator.validate_mutation(
        mutation, working_state, scenario_snapshot
    )
    if not validation.is_valid:
        _log(result_sink, call, arguments, {"error": validation.error_message}, False)
        return working_state
    if result_sink is not None:
        result_sink.mutated_paths.append(path)
    _log(result_sink, call, arguments, {"success": True}, True)
    return validation.updated_state or working_state


def _is_flag_raised(working_state: dict[str, object], rule_id: str) -> bool:
    flags = working_state.get(RULE_FLAGS_ROOT)
    return isinstance(flags, dict) and flags.get(rule_id) is True


def _log(
    result_sink: MasterModeTurnResult | None,
    call: types.FunctionCall,
    arguments: dict[str, object],
    result: dict[str, object],
    is_valid: bool,
) -> None:
    if result_sink is None:
        return
    result_sink.tool_calls.append(
        ToolCallLogEntry(
            tool_name=call.name or "",
            arguments=arguments,
            result=result,
            is_valid=is_valid,
        )
    )
