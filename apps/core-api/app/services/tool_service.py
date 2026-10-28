"""Optional scenario tools: enabling, disabling and the write-path guard."""

import uuid
from collections.abc import Awaitable, Callable

from app.db.models.scenario import Scenario
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.exceptions.tool_exceptions import (
    ToolNotEnabledError,
    ToolRequiredByError,
    ToolsRequireMasterModeError,
)
from app.models.tools import ToolsResponse, ToolsUpdate
from app.repositories.scenario_repo import ScenarioRepo
from app.services.rule_sheet_state import RULE_SHEET_TOOL_KEY, validate_reserved_roots
from app.services.scenario_edit_guard import ensure_not_publishing
from app.tools.registry import (
    TOOLS,
    close_over_requires,
    dependents_of,
    validate_known,
)

InertRowCounter = Callable[[str, uuid.UUID], Awaitable[int]]


def ensure_tool_enabled(scenario: Scenario, tool_key: str) -> None:
    if tool_key not in scenario.enabled_tools:
        raise ToolNotEnabledError(tool_key)


class ToolService:
    def __init__(
        self, scenario_repo: ScenarioRepo, count_rows: InertRowCounter
    ) -> None:
        self.scenario_repo = scenario_repo
        self.count_rows = count_rows

    async def get_tools(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> ToolsResponse:
        scenario = await self._get_owned_scenario(scenario_id, user_id)
        return await self._build_response(scenario, auto_enabled=[])

    async def update_tools(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID, data: ToolsUpdate
    ) -> ToolsResponse:
        scenario = await self._get_owned_scenario(scenario_id, user_id)
        ensure_not_publishing(scenario)
        validate_known(data.enabled_tools)
        if data.enabled_tools and scenario.mode != "master":
            raise ToolsRequireMasterModeError()
        self._ensure_no_required_tool_removed(
            scenario.enabled_tools, data.enabled_tools
        )
        closed, auto_enabled = close_over_requires(data.enabled_tools)
        if RULE_SHEET_TOOL_KEY in closed:
            validate_reserved_roots(scenario.state_schema, closed)
        scenario.enabled_tools = closed
        await self.scenario_repo.update(scenario)
        return await self._build_response(scenario, auto_enabled)

    def _ensure_no_required_tool_removed(
        self, current: list[str], requested: list[str]
    ) -> None:
        for key in current:
            if key in requested:
                continue
            dependents = dependents_of(key, requested)
            if dependents:
                raise ToolRequiredByError(key, dependents)

    async def _build_response(
        self, scenario: Scenario, auto_enabled: list[str]
    ) -> ToolsResponse:
        inert_data: dict[str, int] = {}
        for key in TOOLS:
            if key in scenario.enabled_tools:
                continue
            row_count = await self.count_rows(key, scenario.scenario_id)
            if row_count:
                inert_data[key] = row_count
        return ToolsResponse(
            enabled_tools=list(scenario.enabled_tools),
            auto_enabled=auto_enabled,
            inert_data=inert_data,
        )

    async def _get_owned_scenario(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> Scenario:
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if scenario is None or scenario.status == "archived":
            raise ScenarioNotFoundError()
        if scenario.creator_id != user_id:
            raise ScenarioAccessDeniedError()
        return scenario
