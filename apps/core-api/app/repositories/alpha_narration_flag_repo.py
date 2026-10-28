"""Alpha narration flag persistence."""

import uuid

from app.db.models.alpha_narration_flag import AlphaNarrationFlag
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession


class AlphaNarrationFlagRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        user_id: uuid.UUID,
        playthrough_id: uuid.UUID,
        turn_id: uuid.UUID,
        reasons: list[str],
        note: str | None,
    ) -> AlphaNarrationFlag:
        statement = (
            pg_insert(AlphaNarrationFlag)
            .values(
                user_id=user_id,
                playthrough_id=playthrough_id,
                turn_id=turn_id,
                reasons=reasons,
                note=note,
            )
            .on_conflict_do_update(
                constraint="uq_alpha_narration_flags_user_turn",
                set_={"reasons": reasons, "note": note},
            )
            .returning(AlphaNarrationFlag.flag_id)
        )
        flag_id = (await self._session.execute(statement)).scalar_one()
        return await self._get(flag_id)

    async def _get(self, flag_id: uuid.UUID) -> AlphaNarrationFlag:
        result = await self._session.execute(
            select(AlphaNarrationFlag)
            .where(AlphaNarrationFlag.flag_id == flag_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one()
