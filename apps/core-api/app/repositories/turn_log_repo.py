"""TurnLog data repository for direct database operations."""

import uuid

from app.db.models.turn_log import TurnLog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class TurnLogRepo:
    """Repository managing direct SQLAlchemy queries for TurnLog entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, turn_id: uuid.UUID) -> TurnLog | None:
        """Fetch a single turn by its id."""
        result = await self.session.execute(
            select(TurnLog).where(TurnLog.turn_id == turn_id)
        )
        return result.scalars().first()

    async def list_by_playthrough(
        self,
        playthrough_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        from_turn: int | None = None,
    ) -> tuple[list[TurnLog], int]:
        """Fetch a page of turn history, oldest first, optionally from a turn number."""
        stmt = select(TurnLog).where(TurnLog.playthrough_id == playthrough_id)
        if from_turn is not None:
            stmt = stmt.where(TurnLog.turn_number >= from_turn)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one() or 0

        stmt = stmt.order_by(TurnLog.turn_number.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_latest_narrations(
        self, playthrough_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, str | None]:
        """Fetch the newest turn's narration for each playthrough in one query."""
        if not playthrough_ids:
            return {}
        stmt = (
            select(TurnLog.playthrough_id, TurnLog.narration_text)
            .where(TurnLog.playthrough_id.in_(playthrough_ids))
            .distinct(TurnLog.playthrough_id)
            .order_by(TurnLog.playthrough_id, TurnLog.turn_number.desc())
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
