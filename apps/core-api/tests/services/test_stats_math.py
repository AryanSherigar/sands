from datetime import UTC, date, datetime

from app.services.stats_math import (
    average_rating,
    bucket_turn_counts,
    build_rating_histogram,
    compute_trend,
    fill_series,
    gated_rate,
    safe_rate,
    summarize_turn_counts,
    to_bucket_counts,
)
from app.services.stats_window import StatsWindow


def test_safe_rate_returns_none_without_denominator() -> None:
    assert safe_rate(3, 0) is None
    assert safe_rate(1, 4) == 0.25


def test_gated_rate_hides_value_under_threshold() -> None:
    assert gated_rate(1, 4, is_sample_sufficient=False) is None
    assert gated_rate(1, 4, is_sample_sufficient=True) == 0.25


def test_compute_trend_cases() -> None:
    rise = compute_trend(12, 10)
    assert rise is not None
    assert rise.percent_change == 0.2
    new = compute_trend(5, 0)
    assert new is not None
    assert new.is_new is True
    flat = compute_trend(0, 0)
    assert flat is not None
    assert flat.percent_change == 0.0
    assert compute_trend(3, None) is None
    assert compute_trend(None, 3) is None


def test_summarize_turn_counts_odd_and_even() -> None:
    assert summarize_turn_counts([(2, 1), (4, 1), (9, 1)]) == (5.0, 4.0)
    assert summarize_turn_counts([(2, 2), (6, 2)]) == (4.0, 4.0)
    assert summarize_turn_counts([]) == (None, None)


def test_bucket_turn_counts_labels_and_placement() -> None:
    buckets = bucket_turn_counts(
        [(0, 1), (2, 2), (3, 1), (50, 4)], [1, 3, 5, 10, 20, 50]
    )
    assert [bucket.label for bucket in buckets] == [
        "0",
        "1-2",
        "3-4",
        "5-9",
        "10-19",
        "20-49",
        "50+",
    ]
    assert [bucket.count for bucket in buckets] == [1, 2, 1, 0, 0, 0, 4]


def test_fill_series_daily_fills_gaps() -> None:
    window = StatsWindow(
        start=datetime(2026, 10, 26, 12, tzinfo=UTC),
        end=datetime(2026, 10, 29, 12, tzinfo=UTC),
        bucket="day",
    )
    points = fill_series({date(2026, 10, 27): 3}, window)
    assert [(point.bucket_start, point.plays) for point in points] == [
        (date(2026, 10, 26), 0),
        (date(2026, 10, 27), 3),
        (date(2026, 10, 28), 0),
        (date(2026, 10, 29), 0),
    ]


def test_fill_series_weekly_starts_on_monday() -> None:
    window = StatsWindow(
        start=datetime(2026, 11, 4, tzinfo=UTC),
        end=datetime(2026, 11, 26, tzinfo=UTC),
        bucket="week",
    )
    starts = [point.bucket_start for point in fill_series({}, window)]
    assert starts == [
        date(2026, 11, 2),
        date(2026, 11, 9),
        date(2026, 11, 16),
        date(2026, 11, 23),
    ]


def test_fill_series_all_time_starts_at_first_bucket_or_is_empty() -> None:
    window = StatsWindow(
        start=None, end=datetime(2026, 11, 26, tzinfo=UTC), bucket="week"
    )
    assert fill_series({}, window) == []
    points = fill_series({date(2026, 11, 16): 2}, window)
    assert [point.bucket_start for point in points] == [
        date(2026, 11, 16),
        date(2026, 11, 23),
    ]


def test_to_bucket_counts_keeps_date_part() -> None:
    assert to_bucket_counts([(datetime(2026, 10, 28, 0, 0), 4)]) == {
        date(2026, 10, 28): 4
    }


def test_rating_histogram_and_average() -> None:
    histogram = build_rating_histogram({5: 2, 3: 1}, [1, 2, 3, 4, 5])
    assert [(bucket.rating, bucket.count) for bucket in histogram] == [
        (1, 0),
        (2, 0),
        (3, 1),
        (4, 0),
        (5, 2),
    ]
    assert average_rating({5: 2, 3: 1}) == 13 / 3
    assert average_rating({}) is None
