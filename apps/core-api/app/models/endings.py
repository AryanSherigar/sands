"""Pydantic v2 schemas for the owner-only Endings tab."""

import uuid

from pydantic import BaseModel


class EndingSlot(BaseModel):
    is_found: bool
    title: str | None = None
    outcome_tag: str | None = None


class ScenarioEndings(BaseModel):
    scenario_id: uuid.UUID
    scenario_title: str
    found_count: int
    total_count: int
    slots: list[EndingSlot]


class EndingsResponse(BaseModel):
    scenarios: list[ScenarioEndings]
