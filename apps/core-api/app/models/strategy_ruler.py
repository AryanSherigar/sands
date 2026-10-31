"""Request and response shapes for strategy ruler customization."""

import uuid

from pydantic import BaseModel, Field


class RulerBackstoryRequest(BaseModel):
    scenario_id: uuid.UUID
    faction_id: str
    ruler_name: str
    epithet: str | None = None
    trait_ids: list[str] = Field(default_factory=list)
    ambition_ids: list[str] = Field(default_factory=list)


class RulerBackstoryResponse(BaseModel):
    backstory: str
