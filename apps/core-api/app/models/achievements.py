"""Pydantic v2 schemas for the Achievements tab."""

from datetime import datetime

from pydantic import BaseModel


class AchievementProgress(BaseModel):
    current: int
    target: int


class OwnerAchievementResponse(BaseModel):
    key: str
    name: str
    family: str
    requirement: str
    earned_at: datetime | None = None
    progress: AchievementProgress


class PublicAchievementResponse(BaseModel):
    key: str
    name: str
    family: str
    requirement: str
    earned_at: datetime
