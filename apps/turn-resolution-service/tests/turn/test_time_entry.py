import pytest
from app.turn import time_entry

TOLD_ELEVEN_FIFTY_TWO_PM = 23 * 60 + 52
AM_MINUTES = 11 * 60 + 52
PM_MINUTES = 23 * 60 + 52


@pytest.mark.parametrize(
    "text",
    ["11:52 pm", "11:52pm", "11.52 PM", "11 52 p.m.", "2352", "23:52", " 11:52 PM "],
)
def test_pm_spellings_read_as_the_same_minute(text: str) -> None:
    assert time_entry.parse_clock_text(text) == {PM_MINUTES}


def test_text_without_am_pm_on_a_clock_face_hour_means_either_half_of_the_day() -> None:
    assert time_entry.parse_clock_text("11:52") == {AM_MINUTES, PM_MINUTES}


def test_hour_only_and_compact_forms() -> None:
    assert time_entry.parse_clock_text("6 am") == {6 * 60}
    assert time_entry.parse_clock_text("952") == {9 * 60 + 52, 21 * 60 + 52}
    assert time_entry.parse_clock_text("0009") == {9}


def test_midnight_and_noon_follow_the_twelve_hour_rule() -> None:
    assert time_entry.parse_clock_text("12:09 am") == {9}
    assert time_entry.parse_clock_text("12:09 pm") == {12 * 60 + 9}


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "eleven fifty-two",
        "11:60",
        "25:00",
        "13:00 pm",
        "0:30 am",
        "11:5",
        "11:52:00",
    ],
)
def test_text_that_is_not_a_time_reads_as_nothing(text: str) -> None:
    assert time_entry.parse_clock_text(text) == frozenset()


def test_classify_prefers_the_told_time_over_the_wall_time() -> None:
    assert time_entry.classify_entry("11:52 pm", PM_MINUTES, PM_MINUTES) == "told"


def test_classify_scores_wall_other_and_garbage() -> None:
    wall = 20 * 60 + 17
    assert time_entry.classify_entry("8:17 pm", PM_MINUTES, wall) == "wall"
    assert time_entry.classify_entry("3:33", PM_MINUTES, wall) == "other"
    assert time_entry.classify_entry("abc", PM_MINUTES, wall) == "other"
    assert time_entry.classify_entry("8:17 pm", PM_MINUTES, None) == "other"


def test_format_minute_of_day_uses_a_twelve_hour_clock() -> None:
    assert time_entry.format_minute_of_day(PM_MINUTES) == "11:52 PM"
    assert time_entry.format_minute_of_day(9) == "12:09 AM"
    assert time_entry.format_minute_of_day(12 * 60) == "12:00 PM"


def test_wall_minute_adds_the_shift_clock_to_the_start_and_wraps() -> None:
    params = {"clock_path": "shift_minutes", "clock_start_minute_of_day": 23 * 60}

    assert time_entry.wall_minute_of_day(params, {"shift_minutes": 40}) == 23 * 60 + 40
    assert time_entry.wall_minute_of_day(params, {"shift_minutes": 80}) == 20
    assert time_entry.wall_minute_of_day(params, {}) is None
    assert time_entry.wall_minute_of_day({}, {"shift_minutes": 5}) is None
