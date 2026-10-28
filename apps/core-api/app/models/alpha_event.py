"""Request and response shapes for POST /v1/alpha/events."""

import uuid
from datetime import datetime
from typing import Self

from app.config import settings
from app.models.alpha_event_props import (
    EVENT_PROPS_MODELS,
    AlphaEventName,
    SafeCode,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AlphaEventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: AlphaEventName
    client_ts: datetime | None = None
    playthrough_id: uuid.UUID | None = None
    props: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_props_against_the_registry(self) -> Self:
        validated = EVENT_PROPS_MODELS[self.name].model_validate(self.props)
        self.props = validated.model_dump(mode="json")
        return self


class AlphaEventsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: SafeCode
    events: list[AlphaEventIn] = Field(
        min_length=1, max_length=settings.alpha_event_max_batch
    )


class AlphaEventsAccepted(BaseModel):
    accepted: int
