"""Changing a scenario's visibility and managing who may open a private one."""

import uuid

from app.db.models.scenario import PRIVATE_VISIBILITY, PUBLIC_VISIBILITY, Scenario
from app.exceptions.scenario_exceptions import ScenarioNotFoundError
from app.exceptions.user_exceptions import UserNotFoundError
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo

VISIBILITIES = (PUBLIC_VISIBILITY, PRIVATE_VISIBILITY)


class ScenarioVisibilityService:
    """Playthroughs already started keep the visibility they were pinned with."""

    def __init__(
        self,
        scenario_repo: ScenarioRepo,
        access_repo: ScenarioAccessRepo,
        user_repo: UserRepo,
    ) -> None:
        self.scenario_repo = scenario_repo
        self.access_repo = access_repo
        self.user_repo = user_repo

    async def _get(self, scenario_id: uuid.UUID) -> Scenario:
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError()
        return scenario

    async def set_visibility(self, scenario_id: uuid.UUID, visibility: str) -> Scenario:
        if visibility not in VISIBILITIES:
            raise ValueError(f"visibility must be one of {VISIBILITIES}")
        scenario = await self._get(scenario_id)
        scenario.visibility = visibility
        return await self.scenario_repo.update(scenario)

    async def allow(self, scenario_id: uuid.UUID, user_id: uuid.UUID) -> None:
        await self._get(scenario_id)
        if await self.user_repo.get_by_id(user_id) is None:
            raise UserNotFoundError()
        await self.access_repo.add(scenario_id, user_id)

    async def revoke(self, scenario_id: uuid.UUID, user_id: uuid.UUID) -> None:
        await self._get(scenario_id)
        await self.access_repo.remove(scenario_id, user_id)

    async def allowed_user_ids(self, scenario_id: uuid.UUID) -> list[uuid.UUID]:
        await self._get(scenario_id)
        return await self.access_repo.list_user_ids(scenario_id)
