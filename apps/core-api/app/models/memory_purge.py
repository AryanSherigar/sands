"""Wire models for the greenfield memory service's POST /v1/purge and GET /v1/scopes.

Mirrors apps/memory/app/models/purge.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

PURGE_MAX_IDS = 100


class PurgeRequest(BaseModel):
    playthrough_ids: list[UUID] = Field(default_factory=list)
    scenario_ids: list[UUID] = Field(default_factory=list)


class MemoryPurgeResult(BaseModel):
    playthroughs_purged: int = 0
    templates_purged: int = 0
    templates_retained_in_use: int = 0


class _TimestampedScope(BaseModel):
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def assume_utc_when_naive(cls, value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class PlaythroughScope(_TimestampedScope):
    playthrough_id: UUID


class TemplateScope(_TimestampedScope):
    template_id: UUID
    scenario_id: UUID
    publish_revision: int


class MemoryScopes(BaseModel):
    playthroughs: list[PlaythroughScope]
    templates: list[TemplateScope]
