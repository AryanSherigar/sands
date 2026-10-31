"""Snapshot contribution and inert-row counter for the `rule_sheet` tool."""

import uuid
from collections.abc import Sequence

from app.db.models.scenario import Scenario
from app.db.models.scenario_sheet_rule import ScenarioSheetRule
from app.repositories.sheet_rule_repo import SheetRuleRepo
from app.services.rule_sheet_state import RULE_SHEET_TOOL_KEY, build_schema_extension
from app.tools.data_counters import register_data_counter
from app.tools.registry import STATE_SCHEMA_EXTENSION_KEY, register_snapshot_contributor
from sqlalchemy.ext.asyncio import AsyncSession


def snapshot_sheet_rules(
    scenario: Scenario, rows: Sequence[object]
) -> dict[str, object]:
    rules = [_snapshot_row(row) for row in rows if isinstance(row, ScenarioSheetRule)]
    contribution: dict[str, object] = {"sheet_rules": rules}
    extension = build_schema_extension(rules)
    if extension:
        contribution[STATE_SCHEMA_EXTENSION_KEY] = extension
    return contribution


def _snapshot_row(rule: ScenarioSheetRule) -> dict[str, object]:
    return {
        "rule_id": str(rule.rule_id),
        "key": rule.key,
        "number": rule.number,
        "text": rule.text,
        "corrupted_text": rule.corrupted_text,
        "initial_status": rule.initial_status,
        "source_style": rule.source_style,
        "is_ai_flaggable": rule.is_ai_flaggable,
        "display_order": rule.display_order,
    }


async def count_sheet_rules(session: AsyncSession, scenario_id: uuid.UUID) -> int:
    return await SheetRuleRepo(session).count_by_scenario(scenario_id)


register_snapshot_contributor(RULE_SHEET_TOOL_KEY, snapshot_sheet_rules)
register_data_counter(RULE_SHEET_TOOL_KEY, count_sheet_rules)
