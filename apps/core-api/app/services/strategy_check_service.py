"""Strategy check service: reports publish blockers and warnings for a draft."""

import uuid

from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.exceptions.strategy_map_exceptions import StrategyMapModeError
from app.repositories.scenario_repo import ScenarioRepo
from strategy_contracts.publish_checks import PublishReport, check_publishable
from strategy_contracts.scenario import StrategyScenario

MODE_STRATEGY = "strategy"


class StrategyCheckService:
    def __init__(self, scenario_repo: ScenarioRepo) -> None:
        self.scenario_repo = scenario_repo

    async def check_scenario(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> PublishReport:
        """Run the publish checks without publishing."""
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if scenario is None or scenario.status == "archived":
            raise ScenarioNotFoundError()
        if scenario.creator_id != user_id:
            raise ScenarioAccessDeniedError()
        if scenario.mode != MODE_STRATEGY:
            raise StrategyMapModeError()
        document = StrategyScenario.model_validate(scenario.strategy_document)
        return check_publishable(document)
