"""Rule check domain service: authoring, validation against the state_schema and
tool enforcement. Master mode only (docs/specs/rules-horror-engine/
rule-checks-tool.spec.md)."""

import uuid

from app.db.models.scenario import Scenario
from app.db.models.scenario_rule_check import ScenarioRuleCheck
from app.exceptions.rule_check_exceptions import (
    RuleCheckModeError,
    RuleCheckNotFoundError,
    RuleCheckValidationError,
)
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.models.rule_check import (
    PARAMS_MODELS,
    RuleCheckCreate,
    RuleCheckResponse,
    RuleCheckUpdate,
)
from app.repositories.entity_repo import EntityRepo
from app.repositories.rule_check_repo import RuleCheckRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.expression_validation import (
    validate_expression_field_references,
    validate_mutation_paths,
)
from app.services.rule_sheet_state import with_rule_sheet_roots
from app.services.scenario_edit_guard import ensure_not_publishing
from app.services.state_schema_paths import enum_option_values, field_at_path
from app.services.tool_service import ensure_tool_enabled
from pydantic import ValidationError as PydanticValidationError

RULE_CHECKS_TOOL_KEY = "rule_checks"
_MERGEABLE_FIELDS = (
    "label",
    "kind",
    "trigger_condition_expression",
    "priority",
    "result_path",
    "params",
    "narrator_instruction_template",
)


class RuleCheckService:
    def __init__(
        self,
        rule_check_repo: RuleCheckRepo,
        entity_repo: EntityRepo,
        scenario_repo: ScenarioRepo,
    ) -> None:
        self.rule_check_repo = rule_check_repo
        self.entity_repo = entity_repo
        self.scenario_repo = scenario_repo

    async def create_check(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID, data: RuleCheckCreate
    ) -> RuleCheckResponse:
        scenario = await self._get_editable_scenario(scenario_id, user_id)
        await self._validate_against_schema(scenario, data)
        check = ScenarioRuleCheck(scenario_id=scenario_id, **data.model_dump())
        created = await self.rule_check_repo.create(check)
        return RuleCheckResponse.model_validate(created)

    async def list_checks(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[RuleCheckResponse]:
        await self._get_owned_master_scenario(scenario_id, user_id)
        checks = await self.rule_check_repo.list_by_scenario(scenario_id)
        return [RuleCheckResponse.model_validate(c) for c in checks]

    async def get_check(
        self, scenario_id: uuid.UUID, check_id: uuid.UUID, user_id: uuid.UUID
    ) -> RuleCheckResponse:
        await self._get_owned_master_scenario(scenario_id, user_id)
        check = await self._get_scoped(scenario_id, check_id)
        return RuleCheckResponse.model_validate(check)

    async def update_check(
        self,
        scenario_id: uuid.UUID,
        check_id: uuid.UUID,
        user_id: uuid.UUID,
        data: RuleCheckUpdate,
    ) -> RuleCheckResponse:
        scenario = await self._get_editable_scenario(scenario_id, user_id)
        check = await self._get_scoped(scenario_id, check_id)
        changes = data.model_dump(exclude_unset=True)
        merged = {field: getattr(check, field) for field in _MERGEABLE_FIELDS}
        validated = _validate_merged_shape({**merged, **changes})
        await self._validate_against_schema(scenario, validated)
        for field, value in validated.model_dump().items():
            setattr(check, field, value)
        updated = await self.rule_check_repo.update(check)
        return RuleCheckResponse.model_validate(updated)

    async def delete_check(
        self, scenario_id: uuid.UUID, check_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Deleting inert data is allowed while the tool is off."""
        scenario = await self._get_owned_master_scenario(scenario_id, user_id)
        ensure_not_publishing(scenario)
        check = await self._get_scoped(scenario_id, check_id)
        await self.rule_check_repo.delete(check)

    async def reorder_checks(
        self,
        scenario_id: uuid.UUID,
        user_id: uuid.UUID,
        ordered_check_ids: list[uuid.UUID],
    ) -> list[RuleCheckResponse]:
        await self._get_editable_scenario(scenario_id, user_id)
        checks = await self.rule_check_repo.list_by_scenario(scenario_id)
        checks_by_id = {check.check_id: check for check in checks}
        for priority, check_id in enumerate(ordered_check_ids):
            check = checks_by_id.get(check_id)
            if check is None:
                raise RuleCheckNotFoundError()
            check.priority = priority
        await self.rule_check_repo.save_all()
        return await self.list_checks(scenario_id, user_id)

    async def _validate_against_schema(
        self, scenario: Scenario, data: RuleCheckCreate
    ) -> None:
        entities = await self.entity_repo.list_by_scenario(scenario.scenario_id)
        entities_by_id = {e.entity_id: e for e in entities}
        validation_schema = with_rule_sheet_roots(
            scenario.state_schema, scenario.enabled_tools
        )
        validate_expression_field_references(
            data.trigger_condition_expression,
            validation_schema,
            entities_by_id,
            RuleCheckValidationError,
        )
        params = PARAMS_MODELS[data.kind].model_validate(data.params)
        validate_mutation_paths(
            params.mutation_paths(),
            validation_schema,
            entities_by_id,
            RuleCheckValidationError,
        )
        _validate_results_fit_enum(
            scenario.state_schema, data.result_path, params.result_values()
        )

    async def _get_editable_scenario(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> Scenario:
        scenario = await self._get_owned_master_scenario(scenario_id, user_id)
        ensure_not_publishing(scenario)
        ensure_tool_enabled(scenario, RULE_CHECKS_TOOL_KEY)
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
            raise RuleCheckModeError()
        return scenario

    async def _get_scoped(
        self, scenario_id: uuid.UUID, check_id: uuid.UUID
    ) -> ScenarioRuleCheck:
        check = await self.rule_check_repo.get_by_id(check_id)
        if check is None or check.scenario_id != scenario_id:
            raise RuleCheckNotFoundError()
        return check


def _validate_merged_shape(merged: dict[str, object]) -> RuleCheckCreate:
    try:
        return RuleCheckCreate(**merged)
    except PydanticValidationError as exc:
        raise RuleCheckValidationError(str(exc)) from exc


def _validate_results_fit_enum(
    state_schema: dict[str, object], result_path: str, results: list[str]
) -> None:
    field = field_at_path(state_schema, result_path)
    if field is None or field.get("type") != "enum":
        raise RuleCheckValidationError(
            f"result_path '{result_path}' must be a declared enum state field"
        )
    allowed = enum_option_values(field.get("options"))
    for result in results:
        if result not in allowed:
            raise RuleCheckValidationError(
                f"Result '{result}' is not an option of '{result_path}'"
            )
