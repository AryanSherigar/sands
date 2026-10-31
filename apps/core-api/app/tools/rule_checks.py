"""Snapshot contribution and inert-row counter for the `rule_checks` tool."""

import uuid
from collections.abc import Sequence

from app.db.models.scenario import Scenario
from app.db.models.scenario_rule_check import ScenarioRuleCheck
from app.repositories.rule_check_repo import RuleCheckRepo
from app.tools.data_counters import register_data_counter
from app.tools.registry import register_snapshot_contributor
from sqlalchemy.ext.asyncio import AsyncSession

TOOL_KEY = "rule_checks"


def snapshot_rule_checks(
    scenario: Scenario, rows: Sequence[object]
) -> dict[str, object]:
    return {
        "rule_checks": [
            _snapshot_row(row) for row in rows if isinstance(row, ScenarioRuleCheck)
        ]
    }


def _snapshot_row(check: ScenarioRuleCheck) -> dict[str, object]:
    return {
        "check_id": str(check.check_id),
        "label": check.label,
        "kind": check.kind,
        "trigger_condition_expression": check.trigger_condition_expression,
        "priority": check.priority,
        "result_path": check.result_path,
        "params": check.params,
        "narrator_instruction_template": check.narrator_instruction_template,
    }


async def count_rule_checks(session: AsyncSession, scenario_id: uuid.UUID) -> int:
    return await RuleCheckRepo(session).count_by_scenario(scenario_id)


register_snapshot_contributor(TOOL_KEY, snapshot_rule_checks)
register_data_counter(TOOL_KEY, count_rule_checks)
