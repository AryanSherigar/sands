"""Who may open a scenario: everyone for a public one, the creator and the
allowlist for a private one. A private scenario hides behind "not found" so its
existence is not revealed to anyone else."""

import uuid

from app.config import settings
from app.db.models.scenario import PRIVATE_VISIBILITY, Scenario
from app.exceptions.scenario_exceptions import ScenarioNotFoundError
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.scenario_repo import ScenarioRepo


def is_private(scenario: Scenario) -> bool:
    return scenario.visibility == PRIVATE_VISIBILITY


class ScenarioAccessChecker:
    def __init__(self, access_repo: ScenarioAccessRepo) -> None:
        self.access_repo = access_repo

    async def can_open(self, scenario: Scenario, user_id: uuid.UUID | None) -> bool:
        if not is_private(scenario):
            return True
        if user_id is None:
            return False
        if scenario.creator_id == user_id:
            return True
        return await self.access_repo.is_allowed(scenario.scenario_id, user_id)

    async def ensure_can_open(
        self, scenario: Scenario, user_id: uuid.UUID | None
    ) -> None:
        if not await self.can_open(scenario, user_id):
            raise ScenarioNotFoundError()


async def is_reachable_in_alpha(
    scenario_repo: ScenarioRepo, scenario_id: uuid.UUID
) -> bool:
    """In alpha mode a route may serve the alpha scenario or a private scenario;
    the service behind the route then applies the private scenario's allowlist."""
    if scenario_id == settings.alpha_scenario_id:
        return True
    return await scenario_repo.get_visibility(scenario_id) == PRIVATE_VISIBILITY
