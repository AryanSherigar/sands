"""Wire contract of POST /v1/purge and GET /v1/scopes, plus template GC rows."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

PURGE_MAX_IDS = 100


class PurgeRequest(BaseModel):
    playthrough_ids: list[UUID] = Field(default_factory=list)
    scenario_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_id_count(self) -> Self:
        total = len(self.playthrough_ids) + len(self.scenario_ids)
        if total == 0:
            raise ValueError("at least one playthrough_id or scenario_id is required")
        if total > PURGE_MAX_IDS:
            raise ValueError(f"at most {PURGE_MAX_IDS} ids per request")
        return self


class PurgeResponse(BaseModel):
    playthroughs_purged: int
    templates_purged: int
    templates_retained_in_use: int


class PlaythroughScope(BaseModel):
    playthrough_id: UUID
    created_at: datetime


class TemplateScope(BaseModel):
    template_id: UUID
    scenario_id: UUID
    publish_revision: int
    created_at: datetime


class ScopesResponse(BaseModel):
    playthroughs: list[PlaythroughScope]
    templates: list[TemplateScope]


class TemplateGcCandidate(BaseModel):
    template_id: UUID
    is_referenced: bool
