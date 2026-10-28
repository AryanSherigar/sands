"""Request and response shapes for tester feedback and narration flags."""

import uuid
from typing import Annotated, Literal

from app.db.models.alpha_feedback import FEEDBACK_BODY_MAX_CHARS
from app.db.models.alpha_narration_flag import FLAG_NOTE_MAX_CHARS
from pydantic import BaseModel, ConfigDict, Field

MAX_TURN_NUMBER = 10_000
MAX_FLAG_REASONS = 5

FeedbackCategory = Literal["bug", "confusing", "scary", "other"]
FlagReason = Literal[
    "broke_rule", "contradicted", "out_of_character", "too_long", "other"
]


class AlphaFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    playthrough_id: uuid.UUID
    turn_number: Annotated[int, Field(ge=0, le=MAX_TURN_NUMBER)] | None = None
    category: FeedbackCategory
    body: Annotated[str, Field(min_length=1, max_length=FEEDBACK_BODY_MAX_CHARS)]


class AlphaFeedbackResponse(BaseModel):
    feedback_id: uuid.UUID


class AlphaFlagRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reasons: Annotated[
        list[FlagReason], Field(min_length=1, max_length=MAX_FLAG_REASONS)
    ]
    note: Annotated[str, Field(max_length=FLAG_NOTE_MAX_CHARS)] | None = None


class AlphaFlagResponse(BaseModel):
    flag_id: uuid.UUID
    turn_id: uuid.UUID
    reasons: list[FlagReason]
