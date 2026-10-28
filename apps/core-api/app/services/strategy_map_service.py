"""Strategy map service: validates and stores the region map a creator traced."""

import uuid

from app.db.models.scenario import Scenario
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.exceptions.strategy_map_exceptions import (
    StrategyMapInvalidError,
    StrategyMapModeError,
    StrategyMapNotFoundError,
)
from app.repositories.scenario_repo import ScenarioRepo
from app.services.scenario_edit_guard import ensure_not_publishing
from app.services.strategy_map_validation import (
    FOREIGN_IMAGE_MESSAGE,
    find_map_problems,
    is_map_image_url_allowed,
)
from strategy_contracts.map import MapDocument

MODE_STRATEGY = "strategy"
MAP_KEY = "map"
PROBLEM_SEPARATOR = "; "


class StrategyMapService:
    def __init__(self, scenario_repo: ScenarioRepo) -> None:
        self.scenario_repo = scenario_repo

    async def save_map(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID, document: MapDocument
    ) -> MapDocument:
        """Replaces the scenario's map with the validated document."""
        scenario = await self.scenario_repo.get_by_id_for_update(scenario_id)
        _ensure_strategy_owner(scenario, user_id)
        ensure_not_publishing(scenario)
        _ensure_valid_map(document)
        scenario.strategy_document = {
            **scenario.strategy_document,
            MAP_KEY: document.model_dump(mode="json"),
        }
        await self.scenario_repo.update(scenario)
        return document

    async def get_map(self, scenario_id: uuid.UUID, user_id: uuid.UUID) -> MapDocument:
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        _ensure_strategy_owner(scenario, user_id)
        stored_map = MapDocument.model_validate(
            scenario.strategy_document.get(MAP_KEY, {})
        )
        if not stored_map.regions:
            raise StrategyMapNotFoundError()
        return stored_map


def _ensure_strategy_owner(scenario: Scenario | None, user_id: uuid.UUID) -> None:
    if scenario is None or scenario.status == "archived":
        raise ScenarioNotFoundError()
    if scenario.creator_id != user_id:
        raise ScenarioAccessDeniedError()
    if scenario.mode != MODE_STRATEGY:
        raise StrategyMapModeError()


def _ensure_valid_map(document: MapDocument) -> None:
    if not is_map_image_url_allowed(document.image_url):
        raise StrategyMapInvalidError(FOREIGN_IMAGE_MESSAGE)
    problems = find_map_problems(document)
    if problems:
        raise StrategyMapInvalidError(PROBLEM_SEPARATOR.join(problems))
