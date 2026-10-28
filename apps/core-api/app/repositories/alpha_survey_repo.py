"""Alpha survey response persistence."""

import uuid

from app.db.models.alpha_survey import AlphaSurveyResponse
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession


class AlphaSurveyRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_if_absent(
        self,
        user_id: uuid.UUID,
        playthrough_id: uuid.UUID | None,
        kind: str,
        answers: dict[str, object],
    ) -> bool:
        """Insert a response; return False when the partial unique index already has one."""
        statement = (
            pg_insert(AlphaSurveyResponse)
            .values(
                user_id=user_id,
                playthrough_id=playthrough_id,
                kind=kind,
                answers=answers,
            )
            .on_conflict_do_nothing()
            .returning(AlphaSurveyResponse.response_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None
