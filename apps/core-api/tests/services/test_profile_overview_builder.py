from datetime import UTC, date, datetime, timedelta, timezone

from app.services.profile_overview_builder import (
    EXCERPT_ELLIPSIS,
    EXCERPT_MAX_CHARS,
    build_narration_excerpt,
    build_played_days,
    get_week_bounds,
    get_week_start,
)

MONDAY = date(2026, 10, 26)


def test_week_start_is_monday_for_every_weekday() -> None:
    for offset in range(7):
        now = datetime(2026, 10, 26, 12, 0, tzinfo=UTC) + timedelta(days=offset)
        assert get_week_start(now) == MONDAY


def test_week_start_on_sunday_night_utc_stays_in_same_week() -> None:
    now = datetime(2026, 11, 1, 23, 59, 59, tzinfo=UTC)
    assert get_week_start(now) == MONDAY


def test_week_start_converts_non_utc_input_to_utc() -> None:
    plus_ten = timezone(timedelta(hours=10))
    now = datetime(2026, 11, 2, 5, 0, tzinfo=plus_ten)  # Sunday 19:00 UTC
    assert get_week_start(now) == MONDAY


def test_week_bounds_are_half_open_utc_range() -> None:
    start, end = get_week_bounds(MONDAY)
    assert start == datetime(2026, 10, 26, 0, 0, tzinfo=UTC)
    assert end == datetime(2026, 11, 2, 0, 0, tzinfo=UTC)


def test_played_days_marks_only_played_dates_in_order() -> None:
    days = build_played_days(MONDAY, [date(2026, 10, 26), date(2026, 10, 30)])
    assert days == [True, False, False, False, True, False, False]


def test_played_days_ignores_dates_outside_the_week_and_duplicates() -> None:
    days = build_played_days(
        MONDAY,
        [date(2026, 10, 25), date(2026, 11, 2), date(2026, 10, 27), date(2026, 10, 27)],
    )
    assert days == [False, True, False, False, False, False, False]


def test_played_days_empty_input_is_seven_false() -> None:
    assert build_played_days(MONDAY, []) == [False] * 7


def test_excerpt_none_and_blank_are_none() -> None:
    assert build_narration_excerpt(None) is None
    assert build_narration_excerpt("") is None
    assert build_narration_excerpt("  \n\t  ") is None


def test_excerpt_collapses_whitespace() -> None:
    assert build_narration_excerpt("Rain  falls.\n\nSteam   curls.") == (
        "Rain falls. Steam curls."
    )


def test_excerpt_truncates_with_ellipsis() -> None:
    result = build_narration_excerpt("word " * 200)
    assert result is not None
    assert len(result) <= EXCERPT_MAX_CHARS + len(EXCERPT_ELLIPSIS)
    assert result.endswith(EXCERPT_ELLIPSIS)


def test_excerpt_short_text_is_untouched() -> None:
    assert build_narration_excerpt("A quiet dock.") == "A quiet dock."
