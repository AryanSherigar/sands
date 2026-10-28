"""Compose the owner-only profile Overview from repository aggregates."""

import uuid
from datetime import datetime

from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.models.endings import EndingsResponse
from app.models.profile_overview import (
    ContinueRunSummary,
    LifetimeStatsResponse,
    ProfileOverviewResponse,
    WeeklyActivityResponse,
)
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.profile_overview_repo import ProfileOverviewRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.services.achievement_service import AchievementService
from app.services.endings_service import EndingsService
from app.services.profile_overview_builder import (
    CONTINUE_RUN_LIMIT,
    build_narration_excerpt,
    build_played_days,
    get_week_bounds,
    get_week_start,
)

MASTER_MODE = "master"


def _build_continue_run(
    playthrough: Playthrough, scenario: Scenario, narration: str | None
) -> ContinueRunSummary:
    is_master = scenario.mode == MASTER_MODE
    return ContinueRunSummary(
        playthrough_id=playthrough.playthrough_id,
        scenario_id=scenario.scenario_id,
        scenario_title=scenario.title,
        scenario_mode=scenario.mode,
        primary_genre=scenario.genre_tags[0] if scenario.genre_tags else None,
        turn_count=playthrough.turn_count,
        updated_at=playthrough.updated_at,
        checkpoint=playthrough.checkpoint if is_master else None,
        narration_excerpt=build_narration_excerpt(narration),
    )


class ProfileOverviewService:
    """Builds lifetime stats, weekly activity and continue runs for the owner."""

    def __init__(
        self,
        overview_repo: ProfileOverviewRepo,
        playthrough_repo: PlaythroughRepo,
        turn_log_repo: TurnLogRepo,
        endings_service: EndingsService,
        achievement_service: AchievementService,
    ) -> None:
        self.overview_repo = overview_repo
        self.playthrough_repo = playthrough_repo
        self.turn_log_repo = turn_log_repo
        self.endings_service = endings_service
        self.achievement_service = achievement_service

    async def get_overview(
        self, user_id: uuid.UUID, now: datetime
    ) -> ProfileOverviewResponse:
        """Return the owner's Overview; awards any newly earned badges."""
        endings = await self.endings_service.get_endings(user_id)
        return ProfileOverviewResponse(
            lifetime_stats=await self._build_lifetime_stats(user_id, endings),
            weekly_activity=await self._build_weekly_activity(user_id, now),
            continue_runs=await self._build_continue_runs(user_id),
            recent_milestones=await self.achievement_service.get_recent_milestones(
                user_id, now, endings
            ),
        )

    async def _build_lifetime_stats(
        self, user_id: uuid.UUID, endings: EndingsResponse
    ) -> LifetimeStatsResponse:
        counts = await self.overview_repo.get_lifetime_counts(user_id)
        genres = await self.overview_repo.list_genre_run_counts(user_id)
        stories = endings.scenarios
        return LifetimeStatsResponse(
            turns_taken=counts.turns_taken,
            stories_completed=counts.stories_completed,
            endings_found=sum(story.found_count for story in stories),
            endings_total=sum(story.total_count for story in stories),
            worlds_played=counts.worlds_played,
            campaigns_count=counts.campaigns_count,
            genres_explored=[name for name, _ in genres],
        )

    async def _build_weekly_activity(
        self, user_id: uuid.UUID, now: datetime
    ) -> WeeklyActivityResponse:
        week_start = get_week_start(now)
        start, end = get_week_bounds(week_start)
        dates = await self.overview_repo.list_played_dates(user_id, start, end)
        played_days = build_played_days(week_start, dates)
        return WeeklyActivityResponse(
            week_start=week_start,
            played_days=played_days,
            played_day_count=sum(played_days),
        )

    async def _build_continue_runs(
        self, user_id: uuid.UUID
    ) -> list[ContinueRunSummary]:
        records = await self.playthrough_repo.list_recent_active_with_scenarios(
            user_id, CONTINUE_RUN_LIMIT
        )
        narrations = await self.turn_log_repo.get_latest_narrations(
            [playthrough.playthrough_id for playthrough, _ in records]
        )
        return [
            _build_continue_run(
                playthrough, scenario, narrations.get(playthrough.playthrough_id)
            )
            for playthrough, scenario in records
        ]
