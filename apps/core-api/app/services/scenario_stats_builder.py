import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.config import settings
from app.db.models.scenario import Scenario
from app.models.creator_stats import (
    BenchmarkKey,
    BenchmarkMetric,
    BenchmarkSection,
    EndConditionHit,
    EngagementSection,
    FunnelSection,
    FunnelStep,
    HeatmapMap,
    HeatmapPin,
    OutcomesSection,
    PeerScope,
    PlaysSection,
    ReviewItem,
    ReviewsSection,
    ScenarioStatsResponse,
    ShareCounts,
    StatsRange,
    StatsScenarioSummary,
    VersionRow,
)
from app.repositories.creator_stats_repo import (
    LatestReviewRow,
    MapPinRow,
    PeerMediansRow,
    PlaythroughTotalsRow,
    VersionTotalsRow,
)
from app.services.stats_math import (
    average_rating,
    bucket_turn_counts,
    build_rating_histogram,
    fill_series,
    gated_rate,
    safe_rate,
    summarize_turn_counts,
    to_bucket_counts,
)
from app.services.stats_window import StatsWindow

MASTER_MODE = "master"
SPECTATE_MODE = "spectate"
JOIN_MODE = "join"
FUNNEL_STARTED_LABEL = "Started"
FUNNEL_ENDED_LABEL = "Ended"
FUNNEL_REACHED_LABEL = "Reached turn {threshold}"
GENRE_SCOPE: PeerScope = "genre"
MODE_SCOPE: PeerScope = "mode"


@dataclass(frozen=True)
class PeerMatch:
    scope: PeerScope
    medians: PeerMediansRow


@dataclass(frozen=True)
class ScenarioStatsData:
    totals: PlaythroughTotalsRow | None = None
    series: list[tuple[datetime, int]] = field(default_factory=list)
    turn_frequencies: list[tuple[int, int]] = field(default_factory=list)
    repeat_players: int = 0
    rating_counts: dict[int, int] = field(default_factory=dict)
    latest_reviews: list[LatestReviewRow] = field(default_factory=list)
    bookmark_count: int = 0
    share_counts: dict[str, int] = field(default_factory=dict)
    end_condition_counts: list[tuple[str, int]] = field(default_factory=list)
    version_totals: list[VersionTotalsRow] = field(default_factory=list)
    peer_match: PeerMatch | None = None
    map_pins: list[MapPinRow] = field(default_factory=list)
    discovery_counts: dict[str, int] = field(default_factory=dict)


def empty_totals(scenario_id: uuid.UUID) -> PlaythroughTotalsRow:
    return PlaythroughTotalsRow(
        scenario_id=scenario_id,
        plays=0,
        active_count=0,
        ended_count=0,
        abandoned_count=0,
        win_count=0,
        lose_count=0,
        turn_total=0,
        multiplayer_count=0,
        distinct_players=0,
        reached_turn_counts=tuple(0 for _ in settings.stats_funnel_turn_thresholds),
    )


def is_listed_status(status: str) -> bool:
    return status in settings.stats_listed_statuses


def is_sample_sufficient(totals: PlaythroughTotalsRow) -> bool:
    return totals.plays >= settings.stats_min_sample_playthroughs


def build_scenario_stats(
    scenario: Scenario,
    stats_range: StatsRange,
    window: StatsWindow,
    data: ScenarioStatsData,
) -> ScenarioStatsResponse:
    totals = data.totals or empty_totals(scenario.scenario_id)
    is_sufficient = is_sample_sufficient(totals)
    return ScenarioStatsResponse(
        scenario=_build_summary(scenario),
        stats_range=stats_range,
        bucket=window.bucket,
        is_sample_sufficient=is_sufficient,
        sample_threshold=settings.stats_min_sample_playthroughs,
        plays=_build_plays(totals, data, window, is_sufficient),
        engagement=_build_engagement(data.turn_frequencies, is_sufficient),
        funnel=_build_funnel(totals, data.repeat_players, is_sufficient),
        outcomes=_build_outcomes(
            scenario.mode, totals, data.end_condition_counts, is_sufficient
        ),
        reviews=_build_reviews(data),
        versions=[
            _build_version_row(row, scenario.mode) for row in data.version_totals
        ],
        benchmarks=_build_benchmarks(scenario.mode, totals, data, is_sufficient),
        heatmap=_build_heatmap(scenario.mode, data, totals.plays, is_sufficient),
    )


def _build_summary(scenario: Scenario) -> StatsScenarioSummary:
    return StatsScenarioSummary(
        scenario_id=scenario.scenario_id,
        title=scenario.title,
        status=scenario.status,
        mode=scenario.mode,
        genre_tags=list(scenario.genre_tags),
        has_stats=is_listed_status(scenario.status),
    )


def _build_plays(
    totals: PlaythroughTotalsRow,
    data: ScenarioStatsData,
    window: StatsWindow,
    is_sufficient: bool,
) -> PlaysSection:
    return PlaysSection(
        total_plays=totals.plays,
        active_count=totals.active_count,
        ended_count=totals.ended_count,
        abandoned_count=totals.abandoned_count,
        distinct_players=totals.distinct_players,
        repeat_players=data.repeat_players,
        multiplayer_rate=gated_rate(
            totals.multiplayer_count, totals.plays, is_sufficient
        ),
        series=fill_series(to_bucket_counts(data.series), window),
    )


def _build_engagement(
    frequencies: list[tuple[int, int]], is_sufficient: bool
) -> EngagementSection:
    distribution = bucket_turn_counts(
        frequencies, settings.stats_turn_distribution_edges
    )
    if not is_sufficient:
        return EngagementSection(
            average_turns=None, median_turns=None, turn_distribution=distribution
        )
    average, median = summarize_turn_counts(frequencies)
    return EngagementSection(
        average_turns=average, median_turns=median, turn_distribution=distribution
    )


def _build_funnel(
    totals: PlaythroughTotalsRow, repeat_players: int, is_sufficient: bool
) -> FunnelSection:
    reached_labels = [
        FUNNEL_REACHED_LABEL.format(threshold=threshold)
        for threshold in settings.stats_funnel_turn_thresholds
    ]
    labels = [FUNNEL_STARTED_LABEL, *reached_labels, FUNNEL_ENDED_LABEL]
    counts = [totals.plays, *totals.reached_turn_counts, totals.ended_count]
    steps = [
        FunnelStep(
            label=label,
            count=count,
            rate=gated_rate(count, totals.plays, is_sufficient),
        )
        for label, count in zip(labels, counts, strict=True)
    ]
    return FunnelSection(
        steps=steps,
        retention_rate=gated_rate(
            repeat_players, totals.distinct_players, is_sufficient
        ),
    )


def _build_outcomes(
    mode: str,
    totals: PlaythroughTotalsRow,
    end_condition_counts: list[tuple[str, int]],
    is_sufficient: bool,
) -> OutcomesSection | None:
    if mode != MASTER_MODE:
        return None
    return OutcomesSection(
        win_count=totals.win_count,
        lose_count=totals.lose_count,
        win_rate=gated_rate(totals.win_count, totals.ended_count, is_sufficient),
        lose_rate=gated_rate(totals.lose_count, totals.ended_count, is_sufficient),
        end_conditions=[
            EndConditionHit(
                title=title,
                count=count,
                rate=gated_rate(count, totals.ended_count, is_sufficient),
            )
            for title, count in end_condition_counts
        ],
    )


def _build_reviews(data: ScenarioStatsData) -> ReviewsSection:
    return ReviewsSection(
        review_count=sum(data.rating_counts.values()),
        average_rating=average_rating(data.rating_counts),
        histogram=build_rating_histogram(
            data.rating_counts, settings.stats_rating_scale
        ),
        latest=[to_review_item(row) for row in data.latest_reviews],
        bookmark_count=data.bookmark_count,
        share_counts=ShareCounts(
            spectate=data.share_counts.get(SPECTATE_MODE, 0),
            join=data.share_counts.get(JOIN_MODE, 0),
        ),
    )


def to_review_item(row: LatestReviewRow) -> ReviewItem:
    return ReviewItem(
        scenario_id=row.scenario_id,
        scenario_title=row.scenario_title,
        author_display_name=row.author_display_name,
        rating=row.rating,
        comment=row.comment,
        created_at=row.created_at,
    )


def peer_scopes(scenario: Scenario) -> list[tuple[PeerScope, list[str] | None]]:
    mode_scope: tuple[PeerScope, list[str] | None] = (MODE_SCOPE, None)
    if not scenario.genre_tags:
        return [mode_scope]
    return [(GENRE_SCOPE, list(scenario.genre_tags)), mode_scope]


def _build_version_row(row: VersionTotalsRow, mode: str) -> VersionRow:
    is_sufficient = row.plays >= settings.stats_min_sample_playthroughs
    win_rate = None
    if mode == MASTER_MODE:
        win_rate = gated_rate(row.win_count, row.ended_count, is_sufficient)
    return VersionRow(
        scenario_version=row.scenario_version,
        plays=row.plays,
        completion_rate=gated_rate(row.ended_count, row.plays, is_sufficient),
        win_rate=win_rate,
        average_turns=gated_rate(row.turn_total, row.plays, is_sufficient),
    )


def _build_benchmarks(
    mode: str,
    totals: PlaythroughTotalsRow,
    data: ScenarioStatsData,
    is_sufficient: bool,
) -> BenchmarkSection | None:
    if not is_sufficient or data.peer_match is None:
        return None
    medians = data.peer_match.medians
    return BenchmarkSection(
        peer_count=medians.peer_count,
        peer_scope=data.peer_match.scope,
        metrics=_benchmark_metrics(mode, totals, data.rating_counts, medians),
    )


def _trusted_median(median: float | None, contributing_peers: int) -> float | None:
    # NOTE: Some peers have no value for a metric (no reviews, no endings), and
    # percentile_cont skips them; a median over fewer than the peer minimum
    # could reveal one scenario's number, so it is withheld.
    if contributing_peers < settings.stats_min_benchmark_peers:
        return None
    return median


def _benchmark_metrics(
    mode: str,
    totals: PlaythroughTotalsRow,
    rating_counts: dict[int, int],
    medians: PeerMediansRow,
) -> list[BenchmarkMetric]:
    peer_rating = _trusted_median(medians.average_rating, medians.rating_peer_count)
    pairs: list[tuple[BenchmarkKey, float | None, float | None]] = [
        (
            "completion_rate",
            safe_rate(totals.ended_count, totals.plays),
            medians.completion_rate,
        ),
        (
            "average_turns",
            safe_rate(totals.turn_total, totals.plays),
            medians.average_turns,
        ),
        ("average_rating", average_rating(rating_counts), peer_rating),
    ]
    if mode == MASTER_MODE:
        win_rate = safe_rate(totals.win_count, totals.ended_count)
        peer_win_rate = _trusted_median(medians.win_rate, medians.win_rate_peer_count)
        pairs.append(("win_rate", win_rate, peer_win_rate))
    return [
        BenchmarkMetric(key=key, value=value, peer_median=peer_median)
        for key, value, peer_median in pairs
    ]


def _build_heatmap(
    mode: str, data: ScenarioStatsData, plays: int, is_sufficient: bool
) -> list[HeatmapMap]:
    if mode != MASTER_MODE:
        return []
    maps: dict[uuid.UUID, HeatmapMap] = {}
    for pin in data.map_pins:
        heatmap = maps.setdefault(
            pin.map_id,
            HeatmapMap(
                map_id=pin.map_id, name=pin.map_name, image_url=pin.image_url, pins=[]
            ),
        )
        discovered = data.discovery_counts.get(str(pin.entity_id), 0)
        heatmap.pins.append(
            HeatmapPin(
                entity_id=pin.entity_id,
                name=pin.entity_name,
                x=pin.x,
                y=pin.y,
                discovery_rate=gated_rate(discovered, plays, is_sufficient),
            )
        )
    return list(maps.values())
