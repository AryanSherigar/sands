"""Pydantic v2 schemas for the owner-only profile Overview."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class LifetimeStatsResponse(BaseModel):
    turns_taken: int
    stories_completed: int
    endings_found: int
    endings_total: int
    worlds_played: int
    campaigns_count: int
    genres_explored: list[str]


class WeeklyActivityResponse(BaseModel):
    week_start: date
    played_days: list[bool]
    played_day_count: int


class ContinueRunSummary(BaseModel):
    playthrough_id: uuid.UUID
    scenario_id: uuid.UUID
    scenario_title: str
    scenario_mode: str
    primary_genre: str | None = None
    turn_count: int
    updated_at: datetime
    checkpoint: str | None = None
    narration_excerpt: str | None = None


class MilestoneSummary(BaseModel):
    key: str
    name: str
    earned_at: datetime


class ProfileOverviewResponse(BaseModel):
    lifetime_stats: LifetimeStatsResponse
    weekly_activity: WeeklyActivityResponse
    continue_runs: list[ContinueRunSummary]
    recent_milestones: list[MilestoneSummary]
