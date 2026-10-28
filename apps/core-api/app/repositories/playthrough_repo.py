"""Playthrough data repository for direct database operations."""

import uuid

from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ACTIVE_STATUS = "active"
INITIALIZING_STATUS = "initializing"


class PlaythroughRepo:
    """Repository managing direct SQLAlchemy queries for Playthrough entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, playthrough: Playthrough) -> Playthrough:
        """Persist a new Playthrough entity."""
        self.session.add(playthrough)
        await self.session.flush()
        return playthrough

    async def commit(self) -> None:
        """Make everything flushed so far durable before an external call."""
        await self.session.commit()

    async def get_by_id(self, playthrough_id: uuid.UUID) -> Playthrough | None:
        """Retrieve a playthrough by its primary key ID."""
        stmt = select(Playthrough).where(Playthrough.playthrough_id == playthrough_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_for_update(
        self, playthrough_id: uuid.UUID
    ) -> Playthrough | None:
        """Retrieve a playthrough by primary key with an exclusive row lock (FOR UPDATE)."""
        stmt = (
            select(Playthrough)
            .where(Playthrough.playthrough_id == playthrough_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update(self, playthrough: Playthrough) -> Playthrough:
        """Flush changes to an existing playthrough entity."""
        await self.session.flush()
        await self.session.refresh(playthrough)
        return playthrough

    async def list_by_scenario(self, scenario_id: uuid.UUID) -> list[Playthrough]:
        """Fetch all playthroughs for a given scenario."""
        stmt = select(Playthrough).where(Playthrough.scenario_id == scenario_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user_with_scenarios(
        self, created_by: uuid.UUID, status: str | None = None
    ) -> list[tuple[Playthrough, Scenario]]:
        """Fetch all non-playtest playthroughs with scenario details for a user."""
        stmt = (
            select(Playthrough, Scenario)
            .join(Scenario, Playthrough.scenario_id == Scenario.scenario_id)
            .where(Playthrough.created_by == created_by)
            .where(Playthrough.is_playtest.is_(False))
            .where(Playthrough.status != INITIALIZING_STATUS)
        )
        if status:
            stmt = stmt.where(Playthrough.status == status)
        stmt = stmt.order_by(Playthrough.updated_at.desc())
        result = await self.session.execute(stmt)
        return list(result.all())

    async def list_recent_active_with_scenarios(
        self, created_by: uuid.UUID, limit: int
    ) -> list[tuple[Playthrough, Scenario]]:
        """Fetch a user's most recently updated active non-playtest runs."""
        stmt = (
            select(Playthrough, Scenario)
            .join(Scenario, Playthrough.scenario_id == Scenario.scenario_id)
            .where(Playthrough.created_by == created_by)
            .where(Playthrough.is_playtest.is_(False))
            .where(Playthrough.status == ACTIVE_STATUS)
            .order_by(Playthrough.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.all())
