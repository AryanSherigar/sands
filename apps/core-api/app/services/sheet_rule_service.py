"""Sheet rule domain service: authoring and tool enforcement for the clipboard's
rules. Master mode only (docs/specs/rules-horror-engine/
rules-and-clipboard-tool.spec.md)."""

import uuid

from app.db.models.scenario import Scenario
from app.db.models.scenario_sheet_rule import ScenarioSheetRule
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.exceptions.sheet_rule_exceptions import (
    SheetRuleConflictError,
    SheetRuleModeError,
    SheetRuleNotFoundError,
)
from app.models.sheet_rule import (
    SheetRuleCreate,
    SheetRuleResponse,
    SheetRuleUpdate,
)
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.sheet_rule_repo import SheetRuleRepo
from app.services.rule_sheet_state import RULE_SHEET_TOOL_KEY
from app.services.scenario_edit_guard import ensure_not_publishing
from app.services.tool_service import ensure_tool_enabled


class SheetRuleService:
    def __init__(
        self, sheet_rule_repo: SheetRuleRepo, scenario_repo: ScenarioRepo
    ) -> None:
        self.sheet_rule_repo = sheet_rule_repo
        self.scenario_repo = scenario_repo

    async def create_rule(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID, data: SheetRuleCreate
    ) -> SheetRuleResponse:
        await self._get_editable_scenario(scenario_id, user_id)
        await self._ensure_no_conflict(scenario_id, data.key, data.number)
        rule = ScenarioSheetRule(scenario_id=scenario_id, **data.model_dump())
        created = await self.sheet_rule_repo.create(rule)
        return SheetRuleResponse.model_validate(created)

    async def list_rules(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[SheetRuleResponse]:
        await self._get_owned_master_scenario(scenario_id, user_id)
        rules = await self.sheet_rule_repo.list_by_scenario(scenario_id)
        return [SheetRuleResponse.model_validate(r) for r in rules]

    async def get_rule(
        self, scenario_id: uuid.UUID, rule_id: uuid.UUID, user_id: uuid.UUID
    ) -> SheetRuleResponse:
        await self._get_owned_master_scenario(scenario_id, user_id)
        rule = await self._get_scoped(scenario_id, rule_id)
        return SheetRuleResponse.model_validate(rule)

    async def update_rule(
        self,
        scenario_id: uuid.UUID,
        rule_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SheetRuleUpdate,
    ) -> SheetRuleResponse:
        await self._get_editable_scenario(scenario_id, user_id)
        rule = await self._get_scoped(scenario_id, rule_id)
        changes = data.model_dump(exclude_unset=True)
        is_renumbered = changes.get("number") not in (None, rule.number)
        if is_renumbered:
            await self._ensure_no_conflict(
                scenario_id, None, changes["number"], excluding=rule_id
            )
        for field, value in changes.items():
            setattr(rule, field, value)
        updated = await self.sheet_rule_repo.update(rule)
        return SheetRuleResponse.model_validate(updated)

    async def delete_rule(
        self, scenario_id: uuid.UUID, rule_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Deleting inert data is allowed while the tool is off."""
        scenario = await self._get_owned_master_scenario(scenario_id, user_id)
        ensure_not_publishing(scenario)
        rule = await self._get_scoped(scenario_id, rule_id)
        await self.sheet_rule_repo.delete(rule)

    async def reorder_rules(
        self,
        scenario_id: uuid.UUID,
        user_id: uuid.UUID,
        ordered_rule_ids: list[uuid.UUID],
    ) -> list[SheetRuleResponse]:
        await self._get_editable_scenario(scenario_id, user_id)
        rules = await self.sheet_rule_repo.list_by_scenario(scenario_id)
        by_id = {rule.rule_id: rule for rule in rules}
        if any(rule_id not in by_id for rule_id in ordered_rule_ids):
            raise SheetRuleNotFoundError()
        for position, rule_id in enumerate(ordered_rule_ids):
            by_id[rule_id].display_order = position
        await self.sheet_rule_repo.flush()
        return await self.list_rules(scenario_id, user_id)

    async def _ensure_no_conflict(
        self,
        scenario_id: uuid.UUID,
        key: str | None,
        number: int,
        excluding: uuid.UUID | None = None,
    ) -> None:
        is_taken = await self.sheet_rule_repo.exists_with_key_or_number(
            scenario_id, key, number, excluding
        )
        if is_taken:
            raise SheetRuleConflictError()

    async def _get_editable_scenario(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> Scenario:
        scenario = await self._get_owned_master_scenario(scenario_id, user_id)
        ensure_not_publishing(scenario)
        ensure_tool_enabled(scenario, RULE_SHEET_TOOL_KEY)
        return scenario

    async def _get_owned_master_scenario(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> Scenario:
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if scenario is None or scenario.status == "archived":
            raise ScenarioNotFoundError()
        if scenario.creator_id != user_id:
            raise ScenarioAccessDeniedError()
        if scenario.mode != "master":
            raise SheetRuleModeError()
        return scenario

    async def _get_scoped(
        self, scenario_id: uuid.UUID, rule_id: uuid.UUID
    ) -> ScenarioSheetRule:
        rule = await self.sheet_rule_repo.get_by_id(rule_id)
        if rule is None or rule.scenario_id != scenario_id:
            raise SheetRuleNotFoundError()
        return rule
