"""Alpha event persistence."""

import uuid
from collections.abc import Collection, Sequence

from app.db.models.alpha_event import AlphaEvent
from app.db.models.participant import Participant
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AlphaEventRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, events: Sequence[AlphaEvent]) -> None:
        self._session.add_all(events)
        await self._session.flush()

    async def list_playthroughs_of_user(
        self, user_id: uuid.UUID, playthrough_ids: Collection[uuid.UUID]
    ) -> set[uuid.UUID]:
        """The subset of `playthrough_ids` the user takes part in."""
        if not playthrough_ids:
            return set()
        result = await self._session.execute(
            select(Participant.playthrough_id).where(
                Participant.user_id == user_id,
                Participant.playthrough_id.in_(playthrough_ids),
            )
        )
        return set(result.scalars().all())
