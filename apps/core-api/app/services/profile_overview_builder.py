"""Pure helpers behind the profile Overview response."""

from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta

WEEK_LENGTH_DAYS = 7
CONTINUE_RUN_LIMIT = 2
EXCERPT_MAX_CHARS = 280
EXCERPT_ELLIPSIS = "…"


def get_week_start(now: datetime) -> date:
    today = now.astimezone(UTC).date()
    return today - timedelta(days=today.weekday())


def get_week_bounds(week_start: date) -> tuple[datetime, datetime]:
    start = datetime.combine(week_start, time.min, tzinfo=UTC)
    return start, start + timedelta(days=WEEK_LENGTH_DAYS)


def build_played_days(week_start: date, played_dates: Iterable[date]) -> list[bool]:
    played = set(played_dates)
    return [
        (week_start + timedelta(days=offset)) in played
        for offset in range(WEEK_LENGTH_DAYS)
    ]


def build_narration_excerpt(narration: str | None) -> str | None:
    if not narration:
        return None
    collapsed = " ".join(narration.split())
    if not collapsed:
        return None
    if len(collapsed) <= EXCERPT_MAX_CHARS:
        return collapsed
    return collapsed[:EXCERPT_MAX_CHARS].rstrip() + EXCERPT_ELLIPSIS
