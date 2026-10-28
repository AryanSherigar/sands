"""Evaluate, award and read achievements."""

import uuid
from dataclasses import dataclass
from datetime import datetime

import structlog
from app.models.achievements import (
    AchievementProgress,
    OwnerAchievementResponse,
    PublicAchievementResponse,
)
from app.models.endings import EndingsResponse
from app.models.profile_overview import MilestoneSummary
from app.repositories.achievement_repo import AchievementRepo
from app.repositories.endings_repo import EndingsRepo
from app.repositories.profile_overview_repo import ProfileOverviewRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.achievement_catalogue import (
    ACHIEVEMENT_CATALOGUE,
    CANONICAL_GENRES,
    get_catalogue_index,
    get_definition,
)
from app.services.achievement_rules import (
    AchievementMetrics,
    compute_progress,
    earned_keys,
    pick_best_story,
)
from app.services.endings_service import EndingsService
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

RECENT_MILESTONE_LIMIT = 3
EVENT_EVALUATION_FAILED = "achievement_evaluation_failed"


@dataclass(frozen=True)
class AchievementState:
    progress: dict[str, tuple[int, int]]
    earned: dict[str, datetime]


def _rank_earned(earned: dict[str, datetime]) -> list[str]:
    known = [key for key in earned if get_definition(key) is not None]
    return sorted(known, key=lambda k: (-earned[k].timestamp(), get_catalogue_index(k)))


def _to_milestones(earned: dict[str, datetime]) -> list[MilestoneSummary]:
    milestones: list[MilestoneSummary] = []
    for key in _rank_earned(earned)[:RECENT_MILESTONE_LIMIT]:
        definition = get_definition(key)
        if definition is not None:
            milestones.append(
                MilestoneSummary(key=key, name=definition.name, earned_at=earned[key])
            )
    return milestones


def _stored_state(earned: dict[str, datetime]) -> AchievementState:
    # NOTE: when evaluation fails we cannot know real progress, so earned
    # badges show as complete and the rest as zero rather than failing the tab.
    progress = {
        d.key: (d.target, d.target) if d.key in earned else (0, d.target)
        for d in ACHIEVEMENT_CATALOGUE
    }
    return AchievementState(progress, earned)


class AchievementService:
    """Owns the awarding rules; only owner-triggered paths and events call refresh."""

    def __init__(
        self,
        achievement_repo: AchievementRepo,
        overview_repo: ProfileOverviewRepo,
        endings_service: EndingsService,
        scenario_repo: ScenarioRepo,
    ) -> None:
        self.achievement_repo = achievement_repo
        self.overview_repo = overview_repo
        self.endings_service = endings_service
        self.scenario_repo = scenario_repo

    async def refresh(
        self,
        user_id: uuid.UUID,
        now: datetime,
        endings: EndingsResponse | None = None,
    ) -> AchievementState:
        """Award everything earned so far; safe to call repeatedly."""
        # NOTE: the savepoint keeps a failed evaluation from poisoning the
        # request's transaction, so the endpoint's own queries still run.
        async with self.achievement_repo.session.begin_nested():
            metrics = await self._collect_metrics(user_id, endings)
            progress = compute_progress(metrics)
            await self.achievement_repo.insert_earned(
                user_id, earned_keys(progress), now
            )
            rows = await self.achievement_repo.list_earned(user_id)
        return AchievementState(progress, {row.key: row.earned_at for row in rows})

    async def evaluate_and_award(self, user_id: uuid.UUID, now: datetime) -> None:
        """Best-effort refresh for paths whose real job is something else."""
        try:
            await self.refresh(user_id, now)
        except SQLAlchemyError:
            logger.warning(EVENT_EVALUATION_FAILED, user_id=str(user_id), exc_info=True)

    async def award_scenario_creator(
        self, scenario_id: uuid.UUID, now: datetime
    ) -> None:
        # TRADE-OFF: evaluates the creator on every review, not only 5-star
        # ones; awards are idempotent and this keeps the router free of rules.
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if scenario is not None:
            await self.evaluate_and_award(scenario.creator_id, now)

    async def get_owner_achievements(
        self, user_id: uuid.UUID, now: datetime
    ) -> list[OwnerAchievementResponse]:
        state = await self._refresh_or_stored(user_id, now)
        return [
            OwnerAchievementResponse(
                key=d.key,
                name=d.name,
                family=d.family,
                requirement=d.requirement,
                earned_at=state.earned.get(d.key),
                progress=AchievementProgress(
                    current=state.progress[d.key][0], target=state.progress[d.key][1]
                ),
            )
            for d in ACHIEVEMENT_CATALOGUE
        ]

    async def _refresh_or_stored(
        self, user_id: uuid.UUID, now: datetime
    ) -> AchievementState:
        try:
            return await self.refresh(user_id, now)
        except SQLAlchemyError:
            logger.warning(EVENT_EVALUATION_FAILED, user_id=str(user_id), exc_info=True)
        rows = await self.achievement_repo.list_earned(user_id)
        return _stored_state({row.key: row.earned_at for row in rows})

    async def get_public_achievements(
        self, user_id: uuid.UUID
    ) -> list[PublicAchievementResponse]:
        rows = await self.achievement_repo.list_earned(user_id)
        earned = {row.key: row.earned_at for row in rows}
        return [
            PublicAchievementResponse(
                key=d.key,
                name=d.name,
                family=d.family,
                requirement=d.requirement,
                earned_at=earned[d.key],
            )
            for d in ACHIEVEMENT_CATALOGUE
            if d.key in earned
        ]

    async def get_recent_milestones(
        self,
        user_id: uuid.UUID,
        now: datetime,
        endings: EndingsResponse | None = None,
    ) -> list[MilestoneSummary]:
        try:
            state = await self.refresh(user_id, now, endings)
            return _to_milestones(state.earned)
        except SQLAlchemyError:
            logger.warning(EVENT_EVALUATION_FAILED, user_id=str(user_id), exc_info=True)
        rows = await self.achievement_repo.list_earned(user_id)
        return _to_milestones({row.key: row.earned_at for row in rows})

    async def _collect_metrics(
        self, user_id: uuid.UUID, endings: EndingsResponse | None
    ) -> AchievementMetrics:
        player = await self._collect_player_metrics(user_id, endings)
        creator = await self.achievement_repo.get_creator_metrics(user_id)
        return AchievementMetrics(
            **player,
            published_count=creator.published_count,
            plays_received=creator.plays_received,
            five_star_reviews=await self.achievement_repo.count_five_star_reviews(
                user_id
            ),
        )

    async def _collect_player_metrics(
        self, user_id: uuid.UUID, endings: EndingsResponse | None
    ) -> dict[str, int]:
        counts = await self.overview_repo.get_lifetime_counts(user_id)
        genre_rows = await self.overview_repo.list_genre_run_counts(user_id)
        genres = {name for name, _ in genre_rows}
        stories = (endings or await self.endings_service.get_endings(user_id)).scenarios
        best_found, best_total = pick_best_story(
            [(story.found_count, story.total_count) for story in stories]
        )
        return {
            "turns_taken": counts.turns_taken,
            "stories_completed": counts.stories_completed,
            "wins": await self.achievement_repo.count_wins(user_id),
            "endings_found": sum(story.found_count for story in stories),
            "worlds_played": counts.worlds_played,
            "genres_played": len(genres),
            "canonical_genres_played": len(genres & set(CANONICAL_GENRES)),
            "best_story_found": best_found,
            "best_story_total": best_total,
        }


def build_achievement_service(session: AsyncSession) -> AchievementService:
    return AchievementService(
        achievement_repo=AchievementRepo(session),
        overview_repo=ProfileOverviewRepo(session),
        endings_service=EndingsService(EndingsRepo(session)),
        scenario_repo=ScenarioRepo(session),
    )
