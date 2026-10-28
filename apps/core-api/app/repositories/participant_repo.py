"""Participant data repository for direct database operations."""

import uuid

from app.db.models.participant import Participant
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ParticipantRepo:
    """Repository managing direct SQLAlchemy queries for Participant entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, participant: Participant) -> Participant:
        """Persist a new Participant entity."""
        self.session.add(participant)
        await self.session.flush()
        return participant

    async def list_by_playthrough(self, playthrough_id: uuid.UUID) -> list[Participant]:
        """Fetch all participants of a given playthrough."""
        stmt = select(Participant).where(Participant.playthrough_id == playthrough_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_playthrough_and_user(
        self, playthrough_id: uuid.UUID, user_id: uuid.UUID
    ) -> Participant | None:
        """Retrieve a participant row for a specific user in a playthrough."""
        stmt = select(Participant).where(
            Participant.playthrough_id == playthrough_id,
            Participant.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
