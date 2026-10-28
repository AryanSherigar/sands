"""Aggregate queries behind the alpha health report. Counts only, never text."""

import uuid
from collections.abc import Collection
from datetime import datetime

from app.db.models.alpha_event import AlphaEvent
from app.db.models.alpha_feedback import AlphaFeedback
from app.db.models.alpha_invite import AlphaInvite, AlphaInviteRedemption
from app.db.models.alpha_narration_flag import AlphaNarrationFlag
from app.db.models.alpha_survey import AlphaSurveyResponse
from app.db.models.playthrough import Playthrough
from app.db.models.turn_log import TurnLog
from app.db.models.turn_metrics import TurnMetrics
from app.models.alpha_health import (
    FeedbackCountsRow,
    InviteSeatsRow,
    LatencyRow,
    RunCountsRow,
    TurnTotalsRow,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

MEDIAN = 0.5
P95 = 0.95
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_ABANDONED = "abandoned"
NO_LABEL = "(no invite)"


class AlphaHealthRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_tester_user_ids(self) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(AlphaInviteRedemption.user_id).order_by(
                AlphaInviteRedemption.user_id
            )
        )
        return list(result.scalars().all())

    async def list_run_counts(
        self, user_ids: Collection[uuid.UUID], stale_before: datetime
    ) -> list[RunCountsRow]:
        label = func.coalesce(AlphaInvite.label, NO_LABEL)
        stmt = (
            select(
                label,
                func.count(Playthrough.playthrough_id),
                func.count().filter(Playthrough.status == STATUS_COMPLETED),
                func.count().filter(Playthrough.status == STATUS_ABANDONED),
                func.count().filter(
                    Playthrough.status == STATUS_ACTIVE,
                    Playthrough.updated_at < stale_before,
                ),
            )
            .select_from(Playthrough)
            .outerjoin(
                AlphaInviteRedemption,
                AlphaInviteRedemption.user_id == Playthrough.created_by,
            )
            .outerjoin(
                AlphaInvite, AlphaInvite.invite_id == AlphaInviteRedemption.invite_id
            )
            .where(Playthrough.created_by.in_(user_ids))
            .group_by(label)
            .order_by(label)
        )
        rows = (await self._session.execute(stmt)).all()
        return [RunCountsRow(**_run_counts_fields(row)) for row in rows]

    async def count_endings(self, user_ids: Collection[uuid.UUID]) -> dict[str, int]:
        stmt = (
            select(Playthrough.ended_outcome_tag, func.count())
            .where(
                Playthrough.created_by.in_(user_ids),
                Playthrough.ended_outcome_tag.is_not(None),
            )
            .group_by(Playthrough.ended_outcome_tag)
        )
        return {tag: count for tag, count in (await self._session.execute(stmt)).all()}

    async def get_turn_totals(
        self, user_ids: Collection[uuid.UUID], since: datetime
    ) -> TurnTotalsRow:
        stmt = (
            select(
                func.count(TurnLog.turn_id),
                func.count(TurnLog.turn_id).filter(TurnMetrics.turn_id.is_(None)),
                func.coalesce(func.sum(TurnLog.prompt_tokens), 0),
                func.coalesce(func.sum(TurnLog.completion_tokens), 0),
                func.count(TurnMetrics.turn_id).filter(
                    func.cardinality(TurnMetrics.memory_degraded_reasons) > 0
                ),
                func.count(TurnMetrics.turn_id).filter(
                    TurnMetrics.dropped_mutation_count > 0
                ),
            )
            .select_from(TurnLog)
            .join(Playthrough, Playthrough.playthrough_id == TurnLog.playthrough_id)
            .outerjoin(TurnMetrics, TurnMetrics.turn_id == TurnLog.turn_id)
            .where(Playthrough.created_by.in_(user_ids), TurnLog.created_at >= since)
        )
        row = (await self._session.execute(stmt)).one()
        return TurnTotalsRow(
            turn_count=row[0],
            turns_without_metrics=row[1],
            prompt_tokens=int(row[2]),
            completion_tokens=int(row[3]),
            degraded_turns=row[4],
            dropped_mutation_turns=row[5],
        )

    async def get_latency(
        self, user_ids: Collection[uuid.UUID], since: datetime
    ) -> LatencyRow:
        stmt = (
            select(
                func.percentile_cont(MEDIAN).within_group(TurnMetrics.first_token_ms),
                func.percentile_cont(P95).within_group(TurnMetrics.first_token_ms),
                func.percentile_cont(MEDIAN).within_group(TurnMetrics.total_ms),
                func.percentile_cont(P95).within_group(TurnMetrics.total_ms),
            )
            .select_from(TurnMetrics)
            .join(Playthrough, Playthrough.playthrough_id == TurnMetrics.playthrough_id)
            .where(
                Playthrough.created_by.in_(user_ids), TurnMetrics.created_at >= since
            )
        )
        row = (await self._session.execute(stmt)).one()
        return LatencyRow(
            first_token_p50_ms=row[0],
            first_token_p95_ms=row[1],
            total_p50_ms=row[2],
            total_p95_ms=row[3],
        )

    async def count_degraded_reasons(
        self, user_ids: Collection[uuid.UUID], since: datetime
    ) -> dict[str, int]:
        reasons = (
            select(func.unnest(TurnMetrics.memory_degraded_reasons).label("reason"))
            .select_from(TurnMetrics)
            .join(Playthrough, Playthrough.playthrough_id == TurnMetrics.playthrough_id)
            .where(
                Playthrough.created_by.in_(user_ids), TurnMetrics.created_at >= since
            )
            .subquery()
        )
        stmt = select(reasons.c.reason, func.count()).group_by(reasons.c.reason)
        return {
            name: count for name, count in (await self._session.execute(stmt)).all()
        }

    async def count_retries_by_kind(
        self, user_ids: Collection[uuid.UUID], since: datetime
    ) -> dict[str, int]:
        kind = AlphaEvent.props["kind"].as_string()
        stmt = (
            select(kind, func.count())
            .where(*self._event_filters(user_ids, since, "turn_retry"))
            .group_by(kind)
        )
        return {
            (name or "unknown"): count
            for name, count in (await self._session.execute(stmt)).all()
        }

    async def count_events(
        self, user_ids: Collection[uuid.UUID], since: datetime, name: str
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(AlphaEvent)
            .where(*self._event_filters(user_ids, since, name))
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def get_feedback_counts(
        self, user_ids: Collection[uuid.UUID], since: datetime
    ) -> FeedbackCountsRow:
        return FeedbackCountsRow(
            feedback=await self._count_since(AlphaFeedback, user_ids, since),
            flags=await self._count_since(AlphaNarrationFlag, user_ids, since),
            surveys=await self._count_since(AlphaSurveyResponse, user_ids, since),
        )

    async def list_flagged_turn_ids(
        self, user_ids: Collection[uuid.UUID], since: datetime
    ) -> list[uuid.UUID]:
        stmt = (
            select(AlphaNarrationFlag.turn_id)
            .where(
                AlphaNarrationFlag.user_id.in_(user_ids),
                AlphaNarrationFlag.created_at >= since,
            )
            .order_by(AlphaNarrationFlag.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_invite_seats(self) -> list[InviteSeatsRow]:
        stmt = select(AlphaInvite).order_by(AlphaInvite.label, AlphaInvite.created_at)
        invites = (await self._session.execute(stmt)).scalars().all()
        return [
            InviteSeatsRow(
                label=invite.label,
                seats_used=invite.seats_used,
                max_seats=invite.max_seats,
                is_revoked=invite.revoked_at is not None,
            )
            for invite in invites
        ]

    async def _count_since(
        self, model: type, user_ids: Collection[uuid.UUID], since: datetime
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(model)
            .where(model.user_id.in_(user_ids), model.created_at >= since)
        )
        return (await self._session.execute(stmt)).scalar_one()

    @staticmethod
    def _event_filters(
        user_ids: Collection[uuid.UUID], since: datetime, name: str
    ) -> tuple[object, ...]:
        return (
            AlphaEvent.user_id.in_(user_ids),
            AlphaEvent.name == name,
            AlphaEvent.received_at >= since,
        )


def _run_counts_fields(row: tuple[str, int, int, int, int]) -> dict[str, object]:
    return {
        "label": row[0],
        "started": row[1],
        "completed": row[2],
        "abandoned": row[3],
        "silently_dropped": row[4],
    }
