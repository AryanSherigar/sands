"""Persistence and creator-side aggregates for achievements."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.db.models.playthrough import Playthrough
from app.db.models.review import ScenarioReview
from app.db.models.scenario import Scenario
from app.db.models.user_achievement import UserAchievement
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

WIN_TAG = "win"
FIVE_STAR_RATING = 5


@dataclass(frozen=True)
class EarnedRow:
    key: str
    earned_at: datetime


@dataclass(frozen=True)
class CreatorMetrics:
    published_count: int
    plays_received: int


class AchievementRepo:
    """Repository for user_achievements and the aggregates the badges need."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_earned(self, user_id: uuid.UUID) -> list[EarnedRow]:
        stmt = select(UserAchievement.achievement_key, UserAchievement.earned_at).where(
            UserAchievement.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return [EarnedRow(key, earned_at) for key, earned_at in result.all()]

    async def insert_earned(
        self, user_id: uuid.UUID, keys: list[str], earned_at: datetime
    ) -> list[str]:
        if not keys:
            return []
        stmt = (
            insert(UserAchievement)
            .values(
                [
                    {"user_id": user_id, "achievement_key": key, "earned_at": earned_at}
                    for key in keys
                ]
            )
            .on_conflict_do_nothing(index_elements=["user_id", "achievement_key"])
            .returning(UserAchievement.achievement_key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_wins(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count(Playthrough.playthrough_id)).where(
            Playthrough.created_by == user_id,
            Playthrough.is_playtest.is_(False),
            Playthrough.ended_outcome_tag == WIN_TAG,
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def get_creator_metrics(self, user_id: uuid.UUID) -> CreatorMetrics:
        stmt = select(
            func.count(Scenario.scenario_id),
            func.coalesce(func.sum(Scenario.play_count), 0),
        ).where(
            Scenario.creator_id == user_id,
            Scenario.published_at.is_not(None),
        )
        published, plays = (await self.session.execute(stmt)).one()
        return CreatorMetrics(int(published or 0), int(plays or 0))

    async def count_five_star_reviews(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(ScenarioReview.review_id))
            .join(Scenario, ScenarioReview.scenario_id == Scenario.scenario_id)
            .where(
                Scenario.creator_id == user_id,
                ScenarioReview.rating == FIVE_STAR_RATING,
                ScenarioReview.user_id != user_id,
            )
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)
