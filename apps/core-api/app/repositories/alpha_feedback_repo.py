"""Alpha feedback persistence."""

import uuid

from app.db.models.alpha_feedback import AlphaFeedback
from sqlalchemy.ext.asyncio import AsyncSession


class AlphaFeedbackRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: uuid.UUID,
        playthrough_id: uuid.UUID,
        turn_number: int | None,
        category: str,
        body: str,
    ) -> AlphaFeedback:
        feedback = AlphaFeedback(
            user_id=user_id,
            playthrough_id=playthrough_id,
            turn_number=turn_number,
            category=category,
            body=body,
        )
        self._session.add(feedback)
        await self._session.flush()
        return feedback
