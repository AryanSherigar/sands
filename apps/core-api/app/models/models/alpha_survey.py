"""Fixed question sets for the alpha intake and post-run surveys."""

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

MIN_RATING = 1
MAX_RATING = 5
MAX_FREE_TEXT_CHARS = 500

Rating = Annotated[int, Field(ge=MIN_RATING, le=MAX_RATING)]
FreeText = Annotated[str, Field(max_length=MAX_FREE_TEXT_CHARS)]


class _Answers(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IntakeAnswers(_Answers):
    horror_experience: Literal["none", "some", "a_lot"]
    usual_device: Literal["phone", "tablet", "laptop_or_desktop"]


class PostRunAnswers(_Answers):
    rating: Rating
    scariness: Rating
    confusing: FreeText | None = None
    would_have_stopped: FreeText | None = None


class IntakeSurveyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["intake"]
    answers: IntakeAnswers


class PostRunSurveyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["post_run"]
    playthrough_id: uuid.UUID
    answers: PostRunAnswers


AlphaSurveyRequest = Annotated[
    IntakeSurveyRequest | PostRunSurveyRequest, Field(discriminator="kind")
]


class AlphaSurveyAccepted(BaseModel):
    kind: Literal["intake", "post_run"]
