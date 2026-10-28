"""ScenarioRuleCheck data repository for direct database operations."""

import uuid

from app.db.models.scenario_rule_check import ScenarioRuleCheck
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class RuleCheckRepo:
    """Repository managing direct SQLAlchemy queries for ScenarioRuleCheck."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, check: ScenarioRuleCheck) -> ScenarioRuleCheck:
        self.session.add(check)
        await self.session.flush()
        return check

    async def create_all(self, checks: list[ScenarioRuleCheck]) -> None:
        self.session.add_all(checks)
        await self.session.flush()

    async def get_by_id(self, check_id: uuid.UUID) -> ScenarioRuleCheck | None:
        stmt = select(ScenarioRuleCheck).where(ScenarioRuleCheck.check_id == check_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_scenario(self, scenario_id: uuid.UUID) -> list[ScenarioRuleCheck]:
        """Priority ascending (the queue order for simultaneous triggers),
        creation order breaking ties."""
        stmt = (
            select(ScenarioRuleCheck)
            .where(ScenarioRuleCheck.scenario_id == scenario_id)
            .order_by(ScenarioRuleCheck.priority.asc(), ScenarioRuleCheck.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_scenario(self, scenario_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(ScenarioRuleCheck.scenario_id == scenario_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def save_all(self) -> None:
        """Flush changes made to rows this session already loaded."""
        await self.session.flush()

    async def update(self, check: ScenarioRuleCheck) -> ScenarioRuleCheck:
        await self.session.flush()
        await self.session.refresh(check)
        return check

    async def delete(self, check: ScenarioRuleCheck) -> None:
        await self.session.delete(check)
        await self.session.flush()
