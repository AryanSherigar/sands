"""Pydantic v2 response schemas for creator stats.

Rates are fractions in [0, 1]. A rate, average or median is None when the
scenario (or overview) is under the sample threshold, or has no denominator.
"""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

StatsRange = Literal["7d", "30d", "90d", "all"]
StatsBucket = Literal["day", "week"]
DEFAULT_STATS_RANGE: StatsRange = "30d"
BenchmarkKey = Literal["completion_rate", "average_turns", "average_rating", "win_rate"]
PeerScope = Literal["genre", "mode"]


class Trend(BaseModel):
    percent_change: float | None
    is_new: bool


class SeriesPoint(BaseModel):
    bucket_start: date
    plays: int


class TurnBucket(BaseModel):
    label: str
    count: int


class RatingBucket(BaseModel):
    rating: int
    count: int


class FunnelStep(BaseModel):
    label: str
    count: int
    rate: float | None


class ReviewItem(BaseModel):
    scenario_id: uuid.UUID
    scenario_title: str
    author_display_name: str
    rating: int
    comment: str | None
    created_at: datetime


class ShareCounts(BaseModel):
    spectate: int
    join: int


class StatsScenarioSummary(BaseModel):
    scenario_id: uuid.UUID
    title: str
    status: str
    mode: str
    genre_tags: list[str]
    has_stats: bool


class PlaysSection(BaseModel):
    total_plays: int
    active_count: int
    ended_count: int
    abandoned_count: int
    distinct_players: int
    repeat_players: int
    multiplayer_rate: float | None
    series: list[SeriesPoint]


class EngagementSection(BaseModel):
    average_turns: float | None
    median_turns: float | None
    turn_distribution: list[TurnBucket]


class FunnelSection(BaseModel):
    steps: list[FunnelStep]
    retention_rate: float | None


class EndConditionHit(BaseModel):
    title: str
    count: int
    rate: float | None


class OutcomesSection(BaseModel):
    win_count: int
    lose_count: int
    win_rate: float | None
    lose_rate: float | None
    end_conditions: list[EndConditionHit]


class ReviewsSection(BaseModel):
    review_count: int
    average_rating: float | None
    histogram: list[RatingBucket]
    latest: list[ReviewItem]
    bookmark_count: int
    share_counts: ShareCounts


class VersionRow(BaseModel):
    scenario_version: int
    plays: int
    completion_rate: float | None
    win_rate: float | None
    average_turns: float | None


class BenchmarkMetric(BaseModel):
    key: BenchmarkKey
    value: float | None
    peer_median: float | None


class BenchmarkSection(BaseModel):
    peer_count: int
    peer_scope: PeerScope
    metrics: list[BenchmarkMetric]


class HeatmapPin(BaseModel):
    entity_id: uuid.UUID
    name: str
    x: float
    y: float
    discovery_rate: float | None


class HeatmapMap(BaseModel):
    map_id: uuid.UUID
    name: str
    image_url: str | None
    pins: list[HeatmapPin]


class ScenarioStatsResponse(BaseModel):
    scenario: StatsScenarioSummary
    stats_range: StatsRange
    bucket: StatsBucket
    is_sample_sufficient: bool
    sample_threshold: int
    plays: PlaysSection
    engagement: EngagementSection
    funnel: FunnelSection
    outcomes: OutcomesSection | None
    reviews: ReviewsSection
    versions: list[VersionRow]
    benchmarks: BenchmarkSection | None
    heatmap: list[HeatmapMap]


class HeadlineMetric(BaseModel):
    value: float | None
    trend: Trend | None


class OverviewTotals(BaseModel):
    plays: HeadlineMetric
    players: HeadlineMetric
    average_rating: HeadlineMetric
    completion_rate: HeadlineMetric


class OverviewScenarioRow(BaseModel):
    scenario_id: uuid.UUID
    title: str
    status: str
    plays: int
    trend: Trend | None
    completion_rate: float | None
    average_turns: float | None
    average_rating: float | None


class OverviewHighlight(BaseModel):
    scenario_id: uuid.UUID
    title: str
    value: float


class OverviewHighlights(BaseModel):
    most_played: OverviewHighlight | None
    biggest_drop_off: OverviewHighlight | None
    latest_reviews: list[ReviewItem]


class CreatorStatsOverviewResponse(BaseModel):
    stats_range: StatsRange
    bucket: StatsBucket
    has_published_scenarios: bool
    is_sample_sufficient: bool
    sample_threshold: int
    totals: OverviewTotals
    series: list[SeriesPoint]
    scenarios: list[OverviewScenarioRow]
    highlights: OverviewHighlights
