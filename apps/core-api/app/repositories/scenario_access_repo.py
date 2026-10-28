"""Repository for the private-scenario allowlist."""

import uuid

from app.db.models.scenario_access import ScenarioAccess
from app.db.models.user import User
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


class ScenarioAccessRepo:
    """Direct SQLAlchemy queries for ScenarioAccess rows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def is_allowed(self, scenario_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = select(ScenarioAccess.user_id).where(
            ScenarioAccess.scenario_id == scenario_id,
            ScenarioAccess.user_id == user_id,
        )
        return (await self.session.execute(stmt)).first() is not None

    async def list_user_ids(self, scenario_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = (
            select(ScenarioAccess.user_id)
            .where(ScenarioAccess.scenario_id == scenario_id)
            .order_by(ScenarioAccess.created_at)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def add(self, scenario_id: uuid.UUID, user_id: uuid.UUID) -> None:
        stmt = (
            insert(ScenarioAccess)
            .values(scenario_id=scenario_id, user_id=user_id)
            .on_conflict_do_nothing()
        )
        await self.session.execute(stmt)

    async def remove(self, scenario_id: uuid.UUID, user_id: uuid.UUID) -> None:
        stmt = delete(ScenarioAccess).where(
            ScenarioAccess.scenario_id == scenario_id,
            ScenarioAccess.user_id == user_id,
        )
        await self.session.execute(stmt)

    async def list_members(self, scenario_id: uuid.UUID) -> list[tuple[uuid.UUID, str]]:
        stmt = (
            select(User.user_id, User.display_name)
            .join(ScenarioAccess, ScenarioAccess.user_id == User.user_id)
            .where(ScenarioAccess.scenario_id == scenario_id)
            .order_by(ScenarioAccess.created_at)
        )
        return [
            (row.user_id, row.display_name) for row in await self.session.execute(stmt)
        ]
