"""Queries behind the alpha retention purge."""

import uuid
from collections.abc import Collection

from app.db.models.alpha_event import AlphaEvent
from app.db.models.alpha_feedback import AlphaFeedback
from app.db.models.alpha_invite import AlphaInviteRedemption
from app.db.models.alpha_narration_flag import AlphaNarrationFlag
from app.db.models.alpha_survey import AlphaSurveyResponse
from app.db.models.playthrough import Playthrough
from app.db.models.turn_metrics import TurnMetrics
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

USER_OWNED_MODELS = (
    AlphaNarrationFlag,
    AlphaFeedback,
    AlphaSurveyResponse,
    AlphaEvent,
)


class AlphaPurgeRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_tester_user_ids(self) -> list[uuid.UUID]:
        """Every account that redeemed an alpha invite."""
        result = await self._session.execute(
            select(AlphaInviteRedemption.user_id).order_by(
                AlphaInviteRedemption.user_id
            )
        )
        return list(result.scalars().all())

    async def count_alpha_rows(self, user_ids: Collection[uuid.UUID]) -> dict[str, int]:
        counts = {
            model.__tablename__: await self._count_owned(model, user_ids)
            for model in USER_OWNED_MODELS
        }
        counts[TurnMetrics.__tablename__] = await self._count_metrics(user_ids)
        return counts

    async def delete_alpha_rows(self, user_ids: Collection[uuid.UUID]) -> None:
        for model in USER_OWNED_MODELS:
            await self._session.execute(
                delete(model).where(model.user_id.in_(user_ids))
            )
        await self._session.execute(
            delete(TurnMetrics).where(
                TurnMetrics.playthrough_id.in_(self._runs(user_ids))
            )
        )

    async def _count_owned(self, model: type, user_ids: Collection[uuid.UUID]) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(model).where(model.user_id.in_(user_ids))
        )
        return result.scalar_one()

    async def _count_metrics(self, user_ids: Collection[uuid.UUID]) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(TurnMetrics)
            .where(TurnMetrics.playthrough_id.in_(self._runs(user_ids)))
        )
        return result.scalar_one()

    @staticmethod
    def _runs(user_ids: Collection[uuid.UUID]):
        return select(Playthrough.playthrough_id).where(
            Playthrough.created_by.in_(user_ids)
        )
