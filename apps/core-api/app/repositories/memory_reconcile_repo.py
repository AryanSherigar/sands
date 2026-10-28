"""Live product ids that memory scopes are reconciled against."""

import uuid

from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class MemoryReconcileRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_playthrough_ids(self) -> set[uuid.UUID]:
        result = await self.session.execute(select(Playthrough.playthrough_id))
        return set(result.scalars().all())

    async def list_scenario_ids(self) -> set[uuid.UUID]:
        result = await self.session.execute(select(Scenario.scenario_id))
        return set(result.scalars().all())
