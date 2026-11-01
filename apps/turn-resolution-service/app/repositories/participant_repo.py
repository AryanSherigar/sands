"""Participant data repository for direct database operations."""

import uuid

from app.db.models.participant import Participant
from app.db.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ParticipantRepo:
    """Repository managing direct SQLAlchemy queries for Participant entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, participant_id: uuid.UUID) -> Participant | None:
        """Retrieve a participant by its primary key ID."""
        stmt = select(Participant).where(Participant.participant_id == participant_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_playthrough(self, playthrough_id: uuid.UUID) -> list[Participant]:
        """Fetch all participants of a given playthrough."""
        stmt = select(Participant).where(Participant.playthrough_id == playthrough_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def map_display_names(
        self, playthrough_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        """Map each participant id to its account display name in one query."""
        stmt = (
            select(Participant.participant_id, User.display_name)
            .join(User, User.user_id == Participant.user_id)
            .where(Participant.playthrough_id == playthrough_id)
        )
        result = await self.session.execute(stmt)
        return {row.participant_id: row.display_name for row in result}
