"""ScenarioSheetRule data repository for direct database operations."""

import uuid

from app.db.models.scenario_sheet_rule import ScenarioSheetRule
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class SheetRuleRepo:
    """Repository managing direct SQLAlchemy queries for ScenarioSheetRule."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, rule: ScenarioSheetRule) -> ScenarioSheetRule:
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def create_all(self, rules: list[ScenarioSheetRule]) -> None:
        self.session.add_all(rules)
        await self.session.flush()

    async def get_by_id(self, rule_id: uuid.UUID) -> ScenarioSheetRule | None:
        stmt = select(ScenarioSheetRule).where(ScenarioSheetRule.rule_id == rule_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_scenario(self, scenario_id: uuid.UUID) -> list[ScenarioSheetRule]:
        """The order the rules print on the clipboard: display_order, then number."""
        stmt = (
            select(ScenarioSheetRule)
            .where(ScenarioSheetRule.scenario_id == scenario_id)
            .order_by(ScenarioSheetRule.display_order, ScenarioSheetRule.number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_scenario(self, scenario_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(ScenarioSheetRule.scenario_id == scenario_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists_with_key_or_number(
        self,
        scenario_id: uuid.UUID,
        key: str | None,
        number: int | None,
        excluding_rule_id: uuid.UUID | None = None,
    ) -> bool:
        stmt = select(ScenarioSheetRule.rule_id).where(
            ScenarioSheetRule.scenario_id == scenario_id,
            (ScenarioSheetRule.key == key) | (ScenarioSheetRule.number == number),
        )
        if excluding_rule_id is not None:
            stmt = stmt.where(ScenarioSheetRule.rule_id != excluding_rule_id)
        result = await self.session.execute(stmt.limit(1))
        return result.first() is not None

    async def update(self, rule: ScenarioSheetRule) -> ScenarioSheetRule:
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def delete(self, rule: ScenarioSheetRule) -> None:
        await self.session.delete(rule)
        await self.session.flush()

    async def flush(self) -> None:
        await self.session.flush()
