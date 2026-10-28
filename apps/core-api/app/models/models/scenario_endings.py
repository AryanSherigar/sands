"""Pydantic v2 schemas for a scenario's endings progress shown on its page."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class FoundEndingResponse(BaseModel):
    ending_id: uuid.UUID | None = None
    title: str
    text: str | None = None
    outcome_tag: str | None = None
    turn_reached: int
    found_at: datetime


class ScenarioEndingsResponse(BaseModel):
    """total_count never includes unfound secret endings; found is None when signed out."""

    total_count: int
    found: list[FoundEndingResponse] | None = None
