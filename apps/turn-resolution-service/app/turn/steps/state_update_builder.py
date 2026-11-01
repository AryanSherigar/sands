"""Builds the `state_update` payload: the visible state as of the end of intake.

Sent before narration so the HUD, reader effects and clipboard for a turn match
the state the narrator writes against. A full snapshot of the visible state, not
a diff; the clipboard rides along when the rule sheet is on.
"""

from app.turn.rule_sheet_view import rule_sheet_view
from app.turn.state_visibility import visible_state
from app.turn.tools import is_enabled

RULE_SHEET_TOOL_KEY = "rule_sheet"
RULE_STATUS_ROOT = "rule_status"


def build_state_update(
    scenario_snapshot: dict[str, object], working_state: dict[str, object]
) -> dict[str, object]:
    state_schema = scenario_snapshot.get("state_schema")
    schema = state_schema if isinstance(state_schema, dict) else {}
    payload: dict[str, object] = {"state": visible_state(working_state, schema)}
    if is_enabled(scenario_snapshot, RULE_SHEET_TOOL_KEY):
        payload["rule_sheet"] = _sheet_of(scenario_snapshot, working_state)
    return payload


def _sheet_of(
    scenario_snapshot: dict[str, object], working_state: dict[str, object]
) -> list[dict[str, object]]:
    sheet_rules = scenario_snapshot.get("sheet_rules")
    rule_status = working_state.get(RULE_STATUS_ROOT)
    return rule_sheet_view(
        [rule for rule in sheet_rules if isinstance(rule, dict)]
        if isinstance(sheet_rules, list)
        else [],
        rule_status if isinstance(rule_status, dict) else {},
    )
