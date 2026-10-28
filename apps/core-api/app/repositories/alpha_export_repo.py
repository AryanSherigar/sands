"""Read-only queries behind the alpha data export."""

import uuid
from collections.abc import Collection

from app.db.models.alpha_event import AlphaEvent
from app.db.models.alpha_feedback import AlphaFeedback
from app.db.models.alpha_narration_flag import AlphaNarrationFlag
from app.db.models.alpha_survey import AlphaSurveyResponse
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from app.db.models.turn_metrics import TurnMetrics
from app.db.models.user import User
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession


def _limit_to_playthroughs(
    query: Select, column, playthrough_ids: Collection[uuid.UUID] | None
) -> Select:
    if playthrough_ids is None:
        return query
    return query.where(column.in_(playthrough_ids))


class AlphaExportRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recent_playthrough_ids(
        self,
        user_ids: Collection[uuid.UUID],
        scenario_title: str | None,
        limit: int,
    ) -> list[uuid.UUID]:
        query = select(Playthrough.playthrough_id).where(
            Playthrough.created_by.in_(user_ids)
        )
        if scenario_title is not None:
            query = query.join(
                Scenario, Scenario.scenario_id == Playthrough.scenario_id
            ).where(Scenario.title.ilike(f"%{scenario_title}%"))
        result = await self._session.execute(
            query.order_by(Playthrough.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def list_exportable_user_ids(self, consent_version: str) -> list[uuid.UUID]:
        """Testers on the current consent who have not asked for deletion."""
        result = await self._session.execute(
            select(User.user_id)
            .where(User.alpha_consent_version == consent_version)
            .where(User.deletion_requested_at.is_(None))
            .order_by(User.user_id)
        )
        return list(result.scalars().all())

    async def list_turns(
        self,
        user_ids: Collection[uuid.UUID],
        playthrough_ids: Collection[uuid.UUID] | None = None,
    ) -> list[tuple[TurnLog, Playthrough, TurnMetrics | None]]:
        query = _limit_to_playthroughs(
            select(TurnLog, Playthrough, TurnMetrics)
            .join(Playthrough, Playthrough.playthrough_id == TurnLog.playthrough_id)
            .outerjoin(TurnMetrics, TurnMetrics.turn_id == TurnLog.turn_id)
            .where(Playthrough.created_by.in_(user_ids)),
            TurnLog.playthrough_id,
            playthrough_ids,
        )
        result = await self._session.execute(
            query.order_by(TurnLog.playthrough_id, TurnLog.turn_number)
        )
        return [(turn, run, metrics) for turn, run, metrics in result.all()]

    async def list_metrics(
        self,
        user_ids: Collection[uuid.UUID],
        playthrough_ids: Collection[uuid.UUID] | None = None,
    ) -> list[tuple[TurnMetrics, uuid.UUID]]:
        query = _limit_to_playthroughs(
            select(TurnMetrics, Playthrough.created_by)
            .join(Playthrough, Playthrough.playthrough_id == TurnMetrics.playthrough_id)
            .where(Playthrough.created_by.in_(user_ids)),
            TurnMetrics.playthrough_id,
            playthrough_ids,
        )
        result = await self._session.execute(
            query.order_by(TurnMetrics.playthrough_id, TurnMetrics.turn_number)
        )
        return [(metrics, user_id) for metrics, user_id in result.all()]

    async def list_events(
        self,
        user_ids: Collection[uuid.UUID],
        playthrough_ids: Collection[uuid.UUID] | None = None,
    ) -> list[AlphaEvent]:
        query = _limit_to_playthroughs(
            select(AlphaEvent).where(AlphaEvent.user_id.in_(user_ids)),
            AlphaEvent.playthrough_id,
            playthrough_ids,
        )
        result = await self._session.execute(
            query.order_by(AlphaEvent.user_id, AlphaEvent.received_at)
        )
        return list(result.scalars().all())

    async def list_feedback(
        self,
        user_ids: Collection[uuid.UUID],
        playthrough_ids: Collection[uuid.UUID] | None = None,
    ) -> list[AlphaFeedback]:
        query = _limit_to_playthroughs(
            select(AlphaFeedback).where(AlphaFeedback.user_id.in_(user_ids)),
            AlphaFeedback.playthrough_id,
            playthrough_ids,
        )
        result = await self._session.execute(
            query.order_by(AlphaFeedback.user_id, AlphaFeedback.created_at)
        )
        return list(result.scalars().all())

    async def list_flags(
        self,
        user_ids: Collection[uuid.UUID],
        playthrough_ids: Collection[uuid.UUID] | None = None,
    ) -> list[AlphaNarrationFlag]:
        query = _limit_to_playthroughs(
            select(AlphaNarrationFlag).where(AlphaNarrationFlag.user_id.in_(user_ids)),
            AlphaNarrationFlag.playthrough_id,
            playthrough_ids,
        )
        result = await self._session.execute(
            query.order_by(AlphaNarrationFlag.user_id, AlphaNarrationFlag.created_at)
        )
        return list(result.scalars().all())

    async def list_surveys(
        self,
        user_ids: Collection[uuid.UUID],
        playthrough_ids: Collection[uuid.UUID] | None = None,
    ) -> list[AlphaSurveyResponse]:
        query = _limit_to_playthroughs(
            select(AlphaSurveyResponse).where(
                AlphaSurveyResponse.user_id.in_(user_ids)
            ),
            AlphaSurveyResponse.playthrough_id,
            playthrough_ids,
        )
        result = await self._session.execute(
            query.order_by(AlphaSurveyResponse.user_id, AlphaSurveyResponse.created_at)
        )
        return list(result.scalars().all())
