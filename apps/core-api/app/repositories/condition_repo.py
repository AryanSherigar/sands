"""ScenarioCondition data repository for direct database operations."""

import uuid

from app.db.models.scenario_condition import ScenarioCondition
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class ConditionRepo:
    """Repository managing direct SQLAlchemy queries for ScenarioCondition."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, condition: ScenarioCondition) -> ScenarioCondition:
        """Persist a new ScenarioCondition."""
        self.session.add(condition)
        await self.session.flush()
        return condition

    async def create_all(
        self, conditions: list[ScenarioCondition]
    ) -> list[ScenarioCondition]:
        """Bulk-persist conditions in a single flush (e.g. scenario duplication)."""
        self.session.add_all(conditions)
        await self.session.flush()
        return conditions

    async def get_by_id(self, condition_id: uuid.UUID) -> ScenarioCondition | None:
        """Retrieve a condition by its primary key ID."""
        stmt = select(ScenarioCondition).where(
            ScenarioCondition.condition_id == condition_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_scenario(self, scenario_id: uuid.UUID) -> list[ScenarioCondition]:
        """Retrieve all active conditions belonging to a scenario, in authoring order.

        TRS evaluates conditions in list order against running state, so the order
        must be deterministic: created_at, then condition_id as a tie-breaker.
        """
        stmt = (
            select(ScenarioCondition)
            .where(ScenarioCondition.scenario_id == scenario_id)
            .order_by(ScenarioCondition.created_at, ScenarioCondition.condition_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_with_cues_by_scenario(self, scenario_id: uuid.UUID) -> int:
        """Count a scenario's conditions that carry a sensory cue."""
        stmt = select(func.count()).where(
            ScenarioCondition.scenario_id == scenario_id,
            ScenarioCondition.sensory_cue.is_not(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update(self, condition: ScenarioCondition) -> ScenarioCondition:
        """Flush changes to an existing condition."""
        await self.session.flush()
        await self.session.refresh(condition)
        return condition

    async def delete(self, condition: ScenarioCondition) -> None:
        """Permanently delete a condition."""
        await self.session.delete(condition)
        await self.session.flush()
