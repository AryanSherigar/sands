from datetime import UTC, datetime, timedelta

from app.services.stats_window import build_previous_window, build_stats_window

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


def test_seven_day_window_uses_daily_buckets() -> None:
    window = build_stats_window("7d", NOW)
    assert window.start == NOW - timedelta(days=7)
    assert window.end == NOW
    assert window.bucket == "day"


def test_ninety_day_window_uses_weekly_buckets() -> None:
    assert build_stats_window("90d", NOW).bucket == "week"


def test_all_time_window_has_no_start_and_no_previous() -> None:
    window = build_stats_window("all", NOW)
    assert window.start is None
    assert window.bucket == "week"
    assert build_previous_window(window) is None


def test_previous_window_is_adjacent_and_equal_length() -> None:
    window = build_stats_window("30d", NOW)
    previous = build_previous_window(window)
    assert previous is not None
    assert previous.end == window.start
    assert previous.start == NOW - timedelta(days=60)
    assert previous.bucket == "day"
