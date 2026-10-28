"""Aggregate queries behind the profile Overview tab."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

COMPLETED_STATUS = "completed"
UTC_ZONE = "UTC"
FIRST_TAG_INDEX = 1


@dataclass(frozen=True)
class LifetimeCounts:
    turns_taken: int
    stories_completed: int
    worlds_played: int
    campaigns_count: int


class ProfileOverviewRepo:
    """Repository for the owner-only lifetime, genre and weekly aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_lifetime_counts(self, user_id: uuid.UUID) -> LifetimeCounts:
        stmt = select(
            func.coalesce(func.sum(Playthrough.turn_count), 0),
            func.count(Playthrough.playthrough_id).filter(
                Playthrough.status == COMPLETED_STATUS
            ),
            func.count(Playthrough.scenario_id.distinct()).filter(
                Playthrough.turn_count >= 1
            ),
            func.count(Playthrough.playthrough_id),
        ).where(
            Playthrough.created_by == user_id,
            Playthrough.is_playtest.is_(False),
        )
        row = (await self.session.execute(stmt)).one()
        return LifetimeCounts(*(int(value or 0) for value in row))

    async def list_genre_run_counts(self, user_id: uuid.UUID) -> list[tuple[str, int]]:
        genre = Scenario.genre_tags[FIRST_TAG_INDEX]
        run_count = func.count(Playthrough.playthrough_id)
        stmt = (
            select(genre, run_count)
            .join(Scenario, Playthrough.scenario_id == Scenario.scenario_id)
            .where(
                Playthrough.created_by == user_id,
                Playthrough.is_playtest.is_(False),
                Playthrough.turn_count >= 1,
                genre.is_not(None),
            )
            .group_by(genre)
            .order_by(run_count.desc(), genre.asc())
        )
        result = await self.session.execute(stmt)
        return [(name, int(runs)) for name, runs in result.all()]

    async def list_played_dates(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[date]:
        # NOTE: turns are attributed to the run's creator, so a joined
        # multiplayer participant's turns do not light their own dots.
        # TRADE-OFF: no index on turn_logs.created_at; the join on playthroughs
        # narrows rows first, which is fine until turn_logs grows very large.
        played_on = cast(func.timezone(UTC_ZONE, TurnLog.created_at), Date)
        stmt = (
            select(played_on)
            .select_from(TurnLog)
            .join(Playthrough, TurnLog.playthrough_id == Playthrough.playthrough_id)
            .where(
                Playthrough.created_by == user_id,
                Playthrough.is_playtest.is_(False),
                TurnLog.created_at >= start,
                TurnLog.created_at < end,
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
