from dataclasses import dataclass
from datetime import datetime, timedelta

from app.config import settings
from app.models.creator_stats import StatsBucket, StatsRange

ALL_TIME_RANGE: StatsRange = "all"
DAY_BUCKET: StatsBucket = "day"
WEEK_BUCKET: StatsBucket = "week"


@dataclass(frozen=True)
class StatsWindow:
    start: datetime | None
    end: datetime
    bucket: StatsBucket


def build_stats_window(stats_range: StatsRange, now: datetime) -> StatsWindow:
    if stats_range == ALL_TIME_RANGE:
        return StatsWindow(start=None, end=now, bucket=WEEK_BUCKET)
    days = settings.stats_range_days[stats_range]
    bucket = DAY_BUCKET if days <= settings.stats_daily_bucket_max_days else WEEK_BUCKET
    return StatsWindow(start=now - timedelta(days=days), end=now, bucket=bucket)


def build_previous_window(window: StatsWindow) -> StatsWindow | None:
    if window.start is None:
        return None
    length = window.end - window.start
    return StatsWindow(
        start=window.start - length, end=window.start, bucket=window.bucket
    )
