"""ScenarioMinigame data repository for direct database operations."""

import uuid

from app.db.models.scenario_minigame import ScenarioMinigame
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class MinigameRepo:
    """Repository managing direct SQLAlchemy queries for ScenarioMinigame."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, minigame: ScenarioMinigame) -> ScenarioMinigame:
        """Persist a new minigame."""
        self.session.add(minigame)
        await self.session.flush()
        return minigame

    async def get_by_id(self, minigame_id: uuid.UUID) -> ScenarioMinigame | None:
        """Retrieve a minigame by its primary key ID."""
        stmt = select(ScenarioMinigame).where(
            ScenarioMinigame.minigame_id == minigame_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def count_composure_by_scenario(self, scenario_id: uuid.UUID) -> int:
        """Count a scenario's rhythm_composure minigames."""
        stmt = select(func.count()).where(
            ScenarioMinigame.scenario_id == scenario_id,
            ScenarioMinigame.minigame_type == "rhythm_composure",
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_by_scenario(self, scenario_id: uuid.UUID) -> list[ScenarioMinigame]:
        """Retrieve all minigames for a scenario, ordered by priority ascending."""
        stmt = (
            select(ScenarioMinigame)
            .where(ScenarioMinigame.scenario_id == scenario_id)
            .order_by(ScenarioMinigame.priority.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_scenario(self, scenario_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(ScenarioMinigame.scenario_id == scenario_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update(self, minigame: ScenarioMinigame) -> ScenarioMinigame:
        """Flush changes to an existing minigame."""
        await self.session.flush()
        await self.session.refresh(minigame)
        return minigame

    async def delete(self, minigame: ScenarioMinigame) -> None:
        """Permanently delete a minigame."""
        await self.session.delete(minigame)
        await self.session.flush()
