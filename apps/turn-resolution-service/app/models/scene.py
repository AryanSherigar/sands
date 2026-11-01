"""Request shapes for strategy-mode scene messages."""

from enum import StrEnum
from typing import Self

from app.config import settings
from pydantic import BaseModel, Field, field_validator, model_validator


class SceneMessageKind(StrEnum):
    MESSAGE = "message"
    OPEN = "open"
    SCRIBE = "scribe"
    SEAL = "seal"


KIND_TEXT_LIMITS = {
    SceneMessageKind.MESSAGE: settings.scene_message_max_chars,
    SceneMessageKind.SCRIBE: settings.letter_scribe_instruction_max_chars,
    SceneMessageKind.SEAL: settings.letter_seal_max_chars,
}


class SceneMessageRequest(BaseModel):
    kind: SceneMessageKind = SceneMessageKind.MESSAGE
    text: str = Field(default="", max_length=settings.letter_seal_max_chars)
    current_draft: str = Field(default="", max_length=settings.letter_seal_max_chars)

    @field_validator("text", "current_draft")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def enforce_the_kind_limits(self) -> Self:
        limit = KIND_TEXT_LIMITS.get(self.kind)
        if limit is None:
            return self
        if not self.text:
            raise ValueError("text is required for this kind of message")
        if len(self.text) > limit:
            raise ValueError(f"text is limited to {limit} characters")
        return self
