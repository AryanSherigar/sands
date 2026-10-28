"""Music generation log data repository for direct database operations.

Quota accounting reads: this log is append-only, so usage is always a
COUNT(*) over it rather than a mutable counter.
"""

import uuid
from datetime import datetime

from app.db.models.music_generation_log import MusicGenerationLog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class MusicGenerationLogRepo:
    """Repository managing direct SQLAlchemy queries for MusicGenerationLog."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, scenario_id: uuid.UUID, creator_id: uuid.UUID) -> None:
        """Log a generation attempt, counted whether or not it's later confirmed."""
        self.session.add(
            MusicGenerationLog(scenario_id=scenario_id, creator_id=creator_id)
        )
        await self.session.flush()

    async def acquire_creator_generation_lock(self, creator_id: uuid.UUID) -> None:
        """Serialize concurrent generation requests from the same creator via
        a transaction-scoped Postgres advisory lock, auto-released at this
        session's commit/rollback. Closes the check-then-act race between
        the quota check and log/job creation in
        MusicService.request_generation."""
        await self.session.execute(
            select(func.pg_advisory_xact_lock(func.hashtext(str(creator_id))))
        )

    async def count_by_scenario(self, scenario_id: uuid.UUID) -> int:
        """Count all generation attempts ever logged for a scenario."""
        stmt = (
            select(func.count())
            .select_from(MusicGenerationLog)
            .where(MusicGenerationLog.scenario_id == scenario_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_by_creator_since(
        self, creator_id: uuid.UUID, since: datetime
    ) -> int:
        """Count a creator's generation attempts since the given timestamp."""
        stmt = (
            select(func.count())
            .select_from(MusicGenerationLog)
            .where(
                MusicGenerationLog.creator_id == creator_id,
                MusicGenerationLog.created_at >= since,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
