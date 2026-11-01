"""Playthrough data repository for direct database operations."""

import uuid

from app.db.models.playthrough import Playthrough
from app.exceptions.turn_exceptions import OptimisticLockError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class PlaythroughRepo:
    """Repository managing direct SQLAlchemy queries for Playthrough entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, playthrough_id: uuid.UUID) -> Playthrough | None:
        """Retrieve a playthrough by its primary key ID."""
        stmt = select(Playthrough).where(Playthrough.playthrough_id == playthrough_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_for_update(
        self, playthrough_id: uuid.UUID
    ) -> Playthrough | None:
        """Retrieve a playthrough row under a row lock, refreshed from the database.

        The lock holds until the caller's transaction ends, so concurrent writers
        of the same playthrough serialise on it.
        """
        stmt = (
            select(Playthrough)
            .where(Playthrough.playthrough_id == playthrough_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_state(
        self,
        playthrough_id: uuid.UUID,
        state: dict[str, object],
        new_turn_count: int,
        expected_turn_count: int,
    ) -> None:
        """Update a playthrough's narrative state and turn count with optimistic check."""
        stmt = (
            update(Playthrough)
            .where(
                Playthrough.playthrough_id == playthrough_id,
                Playthrough.turn_count == expected_turn_count,
            )
            .values(state=state, turn_count=new_turn_count)
        )
        result = await self.session.execute(stmt)
        if result.rowcount == 0:
            raise OptimisticLockError()

    async def mark_ended(
        self,
        playthrough_id: uuid.UUID,
        outcome_tag: str,
        outcome_title: str,
        outcome_text: str,
        outcome_id: uuid.UUID | None = None,
        should_commit: bool = True,
    ) -> None:
        """Complete a playthrough with the matched end condition's outcome.

        Commits explicitly: called from inside the SSE generator after
        state_writer's own commit, so nothing else would ever persist this
        write (see state_writer.py's module docstring for why). A caller that
        must add rows to the same transaction passes should_commit=False and
        commits itself.
        """
        await self.session.execute(
            update(Playthrough)
            .where(Playthrough.playthrough_id == playthrough_id)
            .values(
                status="completed",
                ended_outcome_tag=outcome_tag,
                ended_outcome_title=outcome_title,
                ended_outcome_text=outcome_text,
                ended_outcome_id=outcome_id,
            )
        )
        if should_commit:
            await self.session.commit()
