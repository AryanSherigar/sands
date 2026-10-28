import uuid
from dataclasses import dataclass
from datetime import datetime

from app.config import settings
from app.db.models.scenario import Scenario
from app.models.creator_stats import (
    CreatorStatsOverviewResponse,
    HeadlineMetric,
    OverviewHighlight,
    OverviewHighlights,
    OverviewScenarioRow,
    OverviewTotals,
    StatsRange,
    Trend,
)
from app.repositories.creator_stats_repo import LatestReviewRow, PlaythroughTotalsRow
from app.services.scenario_stats_builder import (
    empty_totals,
    is_sample_sufficient,
    to_review_item,
)
from app.services.stats_math import (
    average_rating,
    compute_trend,
    fill_series,
    gated_rate,
    to_bucket_counts,
)
from app.services.stats_window import StatsWindow

RatingRow = tuple[uuid.UUID, int, int]


@dataclass(frozen=True)
class OverviewPeriod:
    totals: list[PlaythroughTotalsRow]
    distinct_players: int
    rating_rows: list[RatingRow]


@dataclass(frozen=True)
class OverviewData:
    scenarios: list[Scenario]
    current: OverviewPeriod
    previous: OverviewPeriod | None
    series: list[tuple[datetime, int]]
    latest_reviews: list[LatestReviewRow]


@dataclass(frozen=True)
class PeriodValues:
    plays: float | None
    players: float | None
    average_rating: float | None
    completion_rate: float | None


NO_PREVIOUS_VALUES = PeriodValues(None, None, None, None)


def build_overview(
    data: OverviewData, stats_range: StatsRange, window: StatsWindow
) -> CreatorStatsOverviewResponse:
    total_plays = sum(row.plays for row in data.current.totals)
    return CreatorStatsOverviewResponse(
        stats_range=stats_range,
        bucket=window.bucket,
        has_published_scenarios=bool(data.scenarios),
        is_sample_sufficient=total_plays >= settings.stats_min_sample_playthroughs,
        sample_threshold=settings.stats_min_sample_playthroughs,
        totals=_build_totals(data.current, data.previous),
        series=fill_series(to_bucket_counts(data.series), window),
        scenarios=_build_rows(data),
        highlights=_build_highlights(data),
    )


def _ratings_by_value(rows: list[RatingRow]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for _, rating, count in rows:
        counts[rating] = counts.get(rating, 0) + count
    return counts


def _period_values(period: OverviewPeriod) -> PeriodValues:
    plays = sum(row.plays for row in period.totals)
    ended = sum(row.ended_count for row in period.totals)
    is_sufficient = plays >= settings.stats_min_sample_playthroughs
    return PeriodValues(
        plays=plays,
        players=period.distinct_players,
        average_rating=average_rating(_ratings_by_value(period.rating_rows)),
        completion_rate=gated_rate(ended, plays, is_sufficient),
    )


def _headline(current: float | None, previous: float | None) -> HeadlineMetric:
    return HeadlineMetric(value=current, trend=compute_trend(current, previous))


def _build_totals(
    current: OverviewPeriod, previous: OverviewPeriod | None
) -> OverviewTotals:
    now = _period_values(current)
    before = _period_values(previous) if previous is not None else NO_PREVIOUS_VALUES
    return OverviewTotals(
        plays=_headline(now.plays, before.plays),
        players=_headline(now.players, before.players),
        average_rating=_headline(now.average_rating, before.average_rating),
        completion_rate=_headline(now.completion_rate, before.completion_rate),
    )


def _build_rows(data: OverviewData) -> list[OverviewScenarioRow]:
    current = {row.scenario_id: row for row in data.current.totals}
    previous: dict[uuid.UUID, PlaythroughTotalsRow] | None = None
    if data.previous is not None:
        previous = {row.scenario_id: row for row in data.previous.totals}
    rows = [
        _build_row(
            scenario,
            current.get(scenario.scenario_id),
            previous,
            data.current.rating_rows,
        )
        for scenario in data.scenarios
    ]
    return sorted(rows, key=lambda row: row.plays, reverse=True)


def _build_row(
    scenario: Scenario,
    totals: PlaythroughTotalsRow | None,
    previous: dict[uuid.UUID, PlaythroughTotalsRow] | None,
    rating_rows: list[RatingRow],
) -> OverviewScenarioRow:
    row_totals = totals or empty_totals(scenario.scenario_id)
    is_sufficient = is_sample_sufficient(row_totals)
    scenario_ratings = [row for row in rating_rows if row[0] == scenario.scenario_id]
    return OverviewScenarioRow(
        scenario_id=scenario.scenario_id,
        title=scenario.title,
        status=scenario.status,
        plays=row_totals.plays,
        trend=_row_trend(row_totals, previous),
        completion_rate=gated_rate(
            row_totals.ended_count, row_totals.plays, is_sufficient
        ),
        average_turns=gated_rate(
            row_totals.turn_total, row_totals.plays, is_sufficient
        ),
        average_rating=average_rating(_ratings_by_value(scenario_ratings)),
    )


def _row_trend(
    totals: PlaythroughTotalsRow,
    previous: dict[uuid.UUID, PlaythroughTotalsRow] | None,
) -> Trend | None:
    if previous is None:
        return None
    previous_totals = previous.get(totals.scenario_id)
    previous_plays = previous_totals.plays if previous_totals else 0
    return compute_trend(totals.plays, previous_plays)


def _build_highlights(data: OverviewData) -> OverviewHighlights:
    titles = {scenario.scenario_id: scenario.title for scenario in data.scenarios}
    sufficient = [row for row in data.current.totals if is_sample_sufficient(row)]
    return OverviewHighlights(
        most_played=_most_played(sufficient, titles),
        biggest_drop_off=_biggest_drop_off(sufficient, titles),
        latest_reviews=[to_review_item(row) for row in data.latest_reviews],
    )


def _most_played(
    totals: list[PlaythroughTotalsRow], titles: dict[uuid.UUID, str]
) -> OverviewHighlight | None:
    if not totals:
        return None
    top = max(totals, key=lambda row: row.plays)
    return OverviewHighlight(
        scenario_id=top.scenario_id, title=titles[top.scenario_id], value=top.plays
    )


def _drop_off_rate(totals: PlaythroughTotalsRow) -> float | None:
    first_step = totals.reached_turn_counts[0]
    last_step = totals.reached_turn_counts[-1]
    if first_step == 0:
        return None
    return 1 - last_step / first_step


def _biggest_drop_off(
    totals: list[PlaythroughTotalsRow], titles: dict[uuid.UUID, str]
) -> OverviewHighlight | None:
    candidates = [
        (rate, row) for row in totals if (rate := _drop_off_rate(row)) is not None
    ]
    if not candidates:
        return None
    rate, row = max(candidates, key=lambda pair: pair[0])
    return OverviewHighlight(
        scenario_id=row.scenario_id, title=titles[row.scenario_id], value=rate
    )
