"""Creator-only stats for one scenario and across a creator's catalogue."""

import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

import structlog
from app.config import settings
from app.db.models.scenario import Scenario
from app.exceptions.scenario_exceptions import ScenarioNotFoundError
from app.models.creator_stats import (
    CreatorStatsOverviewResponse,
    ScenarioStatsResponse,
    StatsRange,
)
from app.repositories.creator_stats_repo import CreatorStatsRepo, PeerFilter
from app.repositories.scenario_repo import ScenarioRepo
from app.services.overview_stats_builder import (
    OverviewData,
    OverviewPeriod,
    build_overview,
)
from app.services.scenario_stats_builder import (
    MASTER_MODE,
    PeerMatch,
    ScenarioStatsData,
    build_scenario_stats,
    empty_totals,
    is_listed_status,
    is_sample_sufficient,
    peer_scopes,
)
from app.services.stats_window import (
    StatsWindow,
    build_previous_window,
    build_stats_window,
)

logger = structlog.get_logger()


def utc_now() -> datetime:
    return datetime.now(UTC)


class CreatorStatsService:
    """Loads aggregation rows and hands them to the pure stats builders."""

    def __init__(
        self,
        stats_repo: CreatorStatsRepo,
        scenario_repo: ScenarioRepo,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.stats_repo = stats_repo
        self.scenario_repo = scenario_repo
        self.clock = clock

    async def get_scenario_stats(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID, stats_range: StatsRange
    ) -> ScenarioStatsResponse:
        """Deep stats for one scenario.

        Raises ScenarioNotFoundError both for a missing scenario and for one the
        caller does not own, so a stats URL never confirms a scenario exists.
        """
        scenario = await self._get_owned_scenario(scenario_id, user_id)
        window = build_stats_window(stats_range, self.clock())
        if not is_listed_status(scenario.status):
            return build_scenario_stats(
                scenario, stats_range, window, ScenarioStatsData()
            )
        core = await self._load_core_data(scenario.scenario_id, window)
        data = await self._with_extended_data(scenario, window, core)
        return build_scenario_stats(scenario, stats_range, window, data)

    async def get_overview(
        self, user_id: uuid.UUID, stats_range: StatsRange
    ) -> CreatorStatsOverviewResponse:
        """Stats across the caller's published and archived scenarios."""
        window = build_stats_window(stats_range, self.clock())
        previous_window = build_previous_window(window)
        scenarios = await self.stats_repo.list_stats_scenarios(
            user_id, settings.stats_listed_statuses
        )
        ids = [scenario.scenario_id for scenario in scenarios]
        previous: OverviewPeriod | None = None
        if previous_window is not None:
            previous = await self._load_period(ids, previous_window)
        data = OverviewData(
            scenarios=scenarios,
            current=await self._load_period(ids, window),
            previous=previous,
            series=await self.stats_repo.get_play_series(
                ids, window.start, window.end, window.bucket
            ),
            latest_reviews=await self.stats_repo.list_latest_reviews(
                ids, window.start, window.end, settings.stats_overview_reviews_limit
            ),
        )
        return build_overview(data, stats_range, window)

    async def _load_period(
        self, ids: list[uuid.UUID], window: StatsWindow
    ) -> OverviewPeriod:
        start, end = window.start, window.end
        return OverviewPeriod(
            totals=await self.stats_repo.get_playthrough_totals(
                ids, start, end, settings.stats_funnel_turn_thresholds
            ),
            distinct_players=await self.stats_repo.count_distinct_players(
                ids, start, end
            ),
            rating_rows=await self.stats_repo.get_rating_counts(ids, start, end),
        )

    async def _get_owned_scenario(
        self, scenario_id: uuid.UUID, user_id: uuid.UUID
    ) -> Scenario:
        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if scenario is None or scenario.creator_id != user_id:
            logger.info(
                "scenario_stats_not_found",
                scenario_id=str(scenario_id),
                user_id=str(user_id),
            )
            raise ScenarioNotFoundError()
        return scenario

    async def _load_core_data(
        self, scenario_id: uuid.UUID, window: StatsWindow
    ) -> ScenarioStatsData:
        ids, start, end = [scenario_id], window.start, window.end
        repo = self.stats_repo
        totals = await repo.get_playthrough_totals(
            ids, start, end, settings.stats_funnel_turn_thresholds
        )
        rating_rows = await repo.get_rating_counts(ids, start, end)
        return ScenarioStatsData(
            totals=totals[0] if totals else None,
            series=await repo.get_play_series(ids, start, end, window.bucket),
            turn_frequencies=await repo.get_turn_count_frequencies(
                scenario_id, start, end
            ),
            repeat_players=await repo.count_repeat_players(
                scenario_id, start, end, settings.stats_repeat_player_min_playthroughs
            ),
            rating_counts={rating: count for _, rating, count in rating_rows},
            latest_reviews=await repo.list_latest_reviews(
                ids, start, end, settings.stats_latest_reviews_limit
            ),
            bookmark_count=await repo.count_bookmarks(scenario_id, start, end),
            share_counts=await repo.get_share_counts(scenario_id, start, end),
        )

    async def _with_extended_data(
        self, scenario: Scenario, window: StatsWindow, core: ScenarioStatsData
    ) -> ScenarioStatsData:
        scenario_id, start, end = scenario.scenario_id, window.start, window.end
        repo = self.stats_repo
        is_master = scenario.mode == MASTER_MODE
        totals = core.totals or empty_totals(scenario_id)
        return replace(
            core,
            end_condition_counts=await repo.get_end_condition_counts(
                scenario_id, start, end
            )
            if is_master
            else [],
            version_totals=await repo.get_version_totals(scenario_id, start, end),
            peer_match=await self._load_peer_match(scenario, window)
            if is_sample_sufficient(totals)
            else None,
            map_pins=await repo.list_map_pins(scenario_id) if is_master else [],
            discovery_counts=await repo.get_discovery_counts(scenario_id, start, end)
            if is_master
            else {},
        )

    async def _load_peer_match(
        self, scenario: Scenario, window: StatsWindow
    ) -> PeerMatch | None:
        # NOTE: At most two queries (genre peers, then mode peers); this loop is
        # a fallback chain, not a per-row fetch.
        for scope, genre_tags in peer_scopes(scenario):
            peer_filter = PeerFilter(
                exclude_scenario_id=scenario.scenario_id,
                mode=scenario.mode,
                genre_tags=genre_tags,
            )
            medians = await self.stats_repo.get_peer_medians(
                peer_filter,
                window.start,
                window.end,
                settings.stats_min_sample_playthroughs,
            )
            if medians.peer_count >= settings.stats_min_benchmark_peers:
                return PeerMatch(scope=scope, medians=medians)
        logger.info(
            "scenario_stats_no_benchmark_peers", scenario_id=str(scenario.scenario_id)
        )
        return None
