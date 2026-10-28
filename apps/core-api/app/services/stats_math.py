from bisect import bisect_right
from datetime import date, datetime, timedelta

from app.models.creator_stats import (
    RatingBucket,
    SeriesPoint,
    StatsBucket,
    Trend,
    TurnBucket,
)
from app.services.stats_window import WEEK_BUCKET, StatsWindow

BUCKET_STEP_DAYS: dict[StatsBucket, int] = {"day": 1, "week": 7}


def safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def gated_rate(
    numerator: int, denominator: int, is_sample_sufficient: bool
) -> float | None:
    if not is_sample_sufficient:
        return None
    return safe_rate(numerator, denominator)


def compute_trend(current: float | None, previous: float | None) -> Trend | None:
    if current is None or previous is None:
        return None
    if previous == 0 and current > 0:
        return Trend(percent_change=None, is_new=True)
    if previous == 0:
        return Trend(percent_change=0.0, is_new=False)
    return Trend(percent_change=(current - previous) / previous, is_new=False)


def summarize_turn_counts(
    frequencies: list[tuple[int, int]],
) -> tuple[float | None, float | None]:
    total = sum(count for _, count in frequencies)
    if total == 0:
        return None, None
    ordered = sorted(frequencies)
    average = sum(turns * count for turns, count in ordered) / total
    lower = _turn_count_at(ordered, (total - 1) // 2)
    upper = _turn_count_at(ordered, total // 2)
    return average, (lower + upper) / 2


def _turn_count_at(ordered_frequencies: list[tuple[int, int]], index: int) -> int:
    seen = 0
    for turns, count in ordered_frequencies:
        seen += count
        if index < seen:
            return turns
    return ordered_frequencies[-1][0]


def bucket_turn_counts(
    frequencies: list[tuple[int, int]], edges: list[int]
) -> list[TurnBucket]:
    labels = _turn_bucket_labels(edges)
    counts = [0] * len(labels)
    for turns, count in frequencies:
        counts[bisect_right(edges, turns)] += count
    return [
        TurnBucket(label=label, count=count)
        for label, count in zip(labels, counts, strict=True)
    ]


def _turn_bucket_labels(edges: list[int]) -> list[str]:
    bounds = [0, *edges]
    labels = [
        _turn_range_label(bounds[i], bounds[i + 1] - 1) for i in range(len(edges))
    ]
    return [*labels, f"{edges[-1]}+"]


def _turn_range_label(low: int, high: int) -> str:
    if low == high:
        return str(low)
    return f"{low}-{high}"


def truncate_to_bucket(day: date, bucket: StatsBucket) -> date:
    if bucket == WEEK_BUCKET:
        return day - timedelta(days=day.weekday())
    return day


def to_bucket_counts(points: list[tuple[datetime, int]]) -> dict[date, int]:
    return {moment.date(): count for moment, count in points}


def fill_series(
    bucket_counts: dict[date, int], window: StatsWindow
) -> list[SeriesPoint]:
    first = _first_bucket(bucket_counts, window)
    if first is None:
        return []
    last = truncate_to_bucket(window.end.date(), window.bucket)
    step = timedelta(days=BUCKET_STEP_DAYS[window.bucket])
    points: list[SeriesPoint] = []
    cursor = first
    while cursor <= last:
        points.append(
            SeriesPoint(bucket_start=cursor, plays=bucket_counts.get(cursor, 0))
        )
        cursor += step
    return points


def _first_bucket(bucket_counts: dict[date, int], window: StatsWindow) -> date | None:
    if window.start is not None:
        return truncate_to_bucket(window.start.date(), window.bucket)
    if not bucket_counts:
        return None
    return min(bucket_counts)


def build_rating_histogram(
    rating_counts: dict[int, int], scale: list[int]
) -> list[RatingBucket]:
    return [
        RatingBucket(rating=rating, count=rating_counts.get(rating, 0))
        for rating in scale
    ]


def average_rating(rating_counts: dict[int, int]) -> float | None:
    total = sum(rating_counts.values())
    if total == 0:
        return None
    return sum(rating * count for rating, count in rating_counts.items()) / total
