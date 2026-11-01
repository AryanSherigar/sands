"""Deterministic reading of a clock time typed by the player (check kind
`time_entry`). No model is involved: the same text always scores the same way.

The parse rules are mirrored by apps/frontend/src/shared/lib/parseClockText.ts,
which only decides whether the "Write it" button is enabled; this module judges.
"""

import re

from app.turn import state_paths

MINUTES_PER_HOUR = 60
MINUTES_PER_HALF_DAY = 720
MINUTES_PER_DAY = 1440
HOURS_PER_HALF_DAY = 12
HOURS_PER_DAY = 24

OUTCOME_TOLD = "told"
OUTCOME_WALL = "wall"
OUTCOME_OTHER = "other"

_CLOCK_PATTERN = re.compile(
    r"^(?P<hour>\d{1,2})(?:[:.\s]?(?P<minute>\d{2}))?\s*(?P<meridiem>[ap])?\.?(?:m\.?)?$"
)
_PM_MARKER = "p"


def parse_clock_text(text: str) -> frozenset[int]:
    """Minutes since midnight the text can mean; empty when it is not a time.

    Text without am/pm on a 1-12 hour means either half of the day, because a
    wall clock face does not say which."""
    match = _CLOCK_PATTERN.match(text.strip().lower())
    if match is None:
        return frozenset()
    hour = int(match.group("hour"))
    minute = int(match.group("minute") or 0)
    if minute >= MINUTES_PER_HOUR:
        return frozenset()
    meridiem = match.group("meridiem")
    if meridiem is not None:
        return _with_meridiem(hour, minute, is_pm=meridiem == _PM_MARKER)
    return _without_meridiem(hour, minute)


def _with_meridiem(hour: int, minute: int, *, is_pm: bool) -> frozenset[int]:
    if not 1 <= hour <= HOURS_PER_HALF_DAY:
        return frozenset()
    base = (hour % HOURS_PER_HALF_DAY) * MINUTES_PER_HOUR + minute
    return frozenset({base + (MINUTES_PER_HALF_DAY if is_pm else 0)})


def _without_meridiem(hour: int, minute: int) -> frozenset[int]:
    if hour >= HOURS_PER_DAY:
        return frozenset()
    base = hour * MINUTES_PER_HOUR + minute
    if 1 <= hour <= HOURS_PER_HALF_DAY:
        face = (hour % HOURS_PER_HALF_DAY) * MINUTES_PER_HOUR + minute
        return frozenset({face, face + MINUTES_PER_HALF_DAY})
    return frozenset({base})


def classify_entry(text: str, told_minute: int, wall_minute: int | None) -> str:
    """Told is checked first, so a told time equal to the wall time still scores
    as the compliant answer."""
    candidates = parse_clock_text(text)
    if told_minute in candidates:
        return OUTCOME_TOLD
    if wall_minute is not None and wall_minute in candidates:
        return OUTCOME_WALL
    return OUTCOME_OTHER


def format_minute_of_day(minute: int) -> str:
    wrapped = minute % MINUTES_PER_DAY
    hour, minute_of_hour = divmod(wrapped, MINUTES_PER_HOUR)
    suffix = "AM" if wrapped < MINUTES_PER_HALF_DAY else "PM"
    return f"{hour % HOURS_PER_HALF_DAY or HOURS_PER_HALF_DAY}:{minute_of_hour:02d} {suffix}"


def wall_minute_of_day(
    params: dict[str, object], state: dict[str, object]
) -> int | None:
    clock_path = params.get("clock_path")
    start = params.get("clock_start_minute_of_day")
    if not isinstance(clock_path, str) or not isinstance(start, int):
        return None
    elapsed = state_paths.get_field_value(state, clock_path)
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)):
        return None
    return (start + int(elapsed)) % MINUTES_PER_DAY
