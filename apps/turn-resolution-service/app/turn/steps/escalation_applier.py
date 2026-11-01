"""Applies the deterministic sanity cost of a free-text escalation.

The narrator only marks the turn ([ESCALATION], see speaker_tags.py); the
penalty is decided here so a weak model can neither skip it nor double it.
"""

import structlog
from app.models.tool_call import MasterModeTurnResult

logger = structlog.get_logger()

ESCALATION_COST = 2
EVENT_ESCALATION_APPLIED = "escalation_applied"
STATE_KEY_SANITY = "sanity"
TOOL_ADJUST_NUMERIC_FIELD = "adjust_numeric_field"
TOOL_SET_FIELD = "set_field"
SANITY_TOOL_NAMES = frozenset({TOOL_ADJUST_NUMERIC_FIELD, TOOL_SET_FIELD})
SUPERSEDED_RESULT = {"superseded": "escalation"}


def apply_escalation(
    turn_start_state: dict[str, object],
    scenario_snapshot: dict[str, object],
    result_sink: MasterModeTurnResult,
) -> None:
    """Replace whatever sanity change the model made with exactly
    ESCALATION_COST off the sanity the turn started with."""
    baseline = turn_start_state.get(STATE_KEY_SANITY)
    if not result_sink.is_escalation_marked or not _is_number(baseline):
        return
    result_sink.final_state[STATE_KEY_SANITY] = _clamp_to_schema_minimum(
        baseline - ESCALATION_COST, scenario_snapshot
    )
    superseded_count = _supersede_model_sanity_calls(result_sink)
    if STATE_KEY_SANITY not in result_sink.mutated_paths:
        result_sink.mutated_paths.append(STATE_KEY_SANITY)
    logger.info(
        EVENT_ESCALATION_APPLIED,
        cost=ESCALATION_COST,
        superseded_model_calls=superseded_count,
    )


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _clamp_to_schema_minimum(
    value: int | float, scenario_snapshot: dict[str, object]
) -> int | float:
    schema = scenario_snapshot.get("state_schema", {}) or {}
    field_def = schema.get(STATE_KEY_SANITY) if isinstance(schema, dict) else None
    minimum = field_def.get("min") if isinstance(field_def, dict) else None
    if _is_number(minimum):
        return max(value, minimum)
    return value


def _supersede_model_sanity_calls(result_sink: MasterModeTurnResult) -> int:
    superseded_count = 0
    for entry in result_sink.tool_calls:
        is_sanity_call = (
            entry.tool_name in SANITY_TOOL_NAMES
            and entry.arguments.get("path") == STATE_KEY_SANITY
        )
        if is_sanity_call and entry.is_valid:
            entry.is_valid = False
            entry.result = dict(SUPERSEDED_RESULT)
            superseded_count += 1
    result_sink.mutated_paths = [
        path for path in result_sink.mutated_paths if path != STATE_KEY_SANITY
    ]
    return superseded_count
