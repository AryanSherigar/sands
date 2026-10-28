"""Active-condition (ScenarioCondition) domain service: business logic,
Effect C state_mutation, and expression field-reference validation."""

import uuid

from app.db.models.scenario import Scenario
from app.db.models.scenario_condition import ScenarioCondition
from app.exceptions.condition_exceptions import (
    ConditionNotFoundError,
    ConditionValidationError,
)
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.models.condition import (
    ConditionCreate,
    ConditionResponse,
    ConditionUpdate,
    StateMutation,
)
from app.repositories.condition_repo import ConditionRepo
from app.repositories.entity_repo import EntityRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.expression_validation import (
    validate_expression_field_references,
    validate_mutation_paths,
)
from app.services.mutation_lists import mutation_columns
from app.services.rule_sheet_state import with_rule_sheet_roots
from app.services.scenario_edit_guard import ensure_not_publishing
from app.services.tool_service import ensure_tool_enabled


def _ensure_cue_tool_enabled(scenario: Scenario, sensory_cue: str | None) -> None:
    if sensory_cue is not None:
        ensure_tool_enabled(scenario, ATMOSPHERE_TOOL_KEY)


def _written_mutations(data: ConditionCreate | ConditionUpdate) -> list[StateMutation]:
    if data.state_mutations:
        return list(data.state_mutations)
    return [data.state_mutation] if data.state_mutation else []


ATMOSPHERE_TOOL_KEY = "atmosphere"


class ConditionService:
    """Service handling active-condition authoring within a master-mode scenario."""

    def __init__(
        self,
        condition_repo: ConditionRepo,
        entity_repo: EntityRepo,
        scenario_repo: ScenarioRepo,
    ) -> None:
        self.condition_repo = condition_repo
        self.entity_repo = entity_repo
        self.scenario_repo = scenario_repo

    async def create_condition(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID, data: ConditionCreate
    ) -> ConditionResponse:
        """Create a new active condition owned by the given scenario."""
        scenario = await self._ensure_editable_scenario(scenario_id, user_id)
        _ensure_cue_tool_enabled(scenario, data.sensory_cue)
        await self._validate_references(scenario_id, scenario, data)

        condition = ScenarioCondition(
            scenario_id=scenario_id,
            label=data.label,
            condition_expression=data.condition_expression,
            narrator_instruction=data.narrator_instruction,
            metadata_=data.metadata,
            is_one_shot=data.is_one_shot,
            sensory_cue=data.sensory_cue,
            cut_ambient=data.cut_ambient,
            silence_duration_ms=data.silence_duration_ms,
            **mutation_columns(
                "state_mutation",
                "state_mutations",
                data.model_fields_set,
                data.state_mutation,
                data.state_mutations,
            ),
        )
        created = await self.condition_repo.create(condition)
        return ConditionResponse.model_validate(created)

    async def list_conditions(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[ConditionResponse]:
        """List all active conditions for a scenario."""
        await self._ensure_scenario_owner(scenario_id, user_id)
        conditions = await self.condition_repo.list_by_scenario(scenario_id)
        return [ConditionResponse.model_validate(c) for c in conditions]

    async def get_condition(
        self, scenario_id: uuid.UUID, condition_id: uuid.UUID, user_id: uuid.UUID
    ) -> ConditionResponse:
        """Fetch a single active condition, scoped to its owning scenario."""
        await self._ensure_scenario_owner(scenario_id, user_id)
        condition = await self._get_scoped_condition(scenario_id, condition_id)
        return ConditionResponse.model_validate(condition)

    async def update_condition(
        self,
        scenario_id: uuid.UUID,
        condition_id: uuid.UUID,
        user_id: uuid.UUID,
        data: ConditionUpdate,
    ) -> ConditionResponse:
        """Update an active condition's mutable fields."""
        scenario = await self._ensure_editable_scenario(scenario_id, user_id)
        condition = await self._get_scoped_condition(scenario_id, condition_id)
        _ensure_cue_tool_enabled(scenario, data.sensory_cue)
        await self._validate_references(scenario_id, scenario, data)

        update_dict = data.model_dump(exclude_unset=True)
        update_dict.pop("state_mutation", None)
        update_dict.pop("state_mutations", None)
        update_dict.update(
            mutation_columns(
                "state_mutation",
                "state_mutations",
                data.model_fields_set,
                data.state_mutation,
                data.state_mutations,
            )
        )
        if "metadata" in update_dict:
            update_dict["metadata_"] = update_dict.pop("metadata")

        for field, value in update_dict.items():
            setattr(condition, field, value)

        updated = await self.condition_repo.update(condition)
        return ConditionResponse.model_validate(updated)

    async def delete_condition(
        self, scenario_id: uuid.UUID, condition_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Delete an active condition."""
        await self._ensure_editable_scenario(scenario_id, user_id)
        condition = await self._get_scoped_condition(scenario_id, condition_id)
        await self.condition_repo.delete(condition)

    async def _validate_references(
        self,
        scenario_id: uuid.UUID,
        scenario: Scenario,
        data: ConditionCreate | ConditionUpdate,
    ) -> None:
        """Validate condition_expression and every mutation path's references."""
        mutations = _written_mutations(data)
        if data.condition_expression is None and not mutations:
            return
        entities = await self.entity_repo.list_by_scenario(scenario_id)
        entities_by_id = {e.entity_id: e for e in entities}
        state_schema = with_rule_sheet_roots(
            scenario.state_schema, scenario.enabled_tools
        )

        if data.condition_expression is not None:
            validate_expression_field_references(
                data.condition_expression,
                state_schema,
                entities_by_id,
                ConditionValidationError,
            )
        if data.state_mutations:
            validate_mutation_paths(
                [mutation.path for mutation in data.state_mutations],
                state_schema,
                entities_by_id,
                ConditionValidationError,
            )
        elif data.state_mutation is not None:
            validate_expression_field_references(
                {"field": data.state_mutation.path},
                state_schema,
                entities_by_id,
                ConditionValidationError,
            )

    async def _get_scoped_condition(
        self, scenario_id: uuid.UUID, condition_id: uuid.UUID
    ) -> ScenarioCondition:
        """Fetch a condition, raising 404 if missing or owned by another scenario."""
        condition = await self.condition_repo.get_by_id(condition_id)
        if condition is None or condition.scenario_id != scenario_id:
            raise ConditionNotFoundError()
        return condition

    async def _ensure_editable_scenario(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> Scenario:
        scenario = await self._ensure_scenario_owner(scenario_id, user_id)
        ensure_not_publishing(scenario)
        return scenario

    async def _ensure_scenario_owner(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> Scenario:
        """Verify the scenario exists and the requesting user is its creator."""
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if scenario is None or scenario.status == "archived":
            raise ScenarioNotFoundError()
        if scenario.creator_id != user_id:
            raise ScenarioAccessDeniedError()
        return scenario
