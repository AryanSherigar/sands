"""Request shapes for strategy-mode scene messages."""

from enum import StrEnum
from typing import Self

from app.config import settings
from pydantic import BaseModel, Field, field_validator, model_validator
from strategy_contracts.judgment import (
    NUANCES_BY_VERDICT,
    JudgmentNuance,
    JudgmentVerdict,
)


class SceneMessageKind(StrEnum):
    MESSAGE = "message"
    OPEN = "open"
    SCRIBE = "scribe"
    SEAL = "seal"
    PRONOUNCE = "pronounce"


KIND_TEXT_LIMITS = {
    SceneMessageKind.MESSAGE: settings.scene_message_max_chars,
    SceneMessageKind.SCRIBE: settings.letter_scribe_instruction_max_chars,
    SceneMessageKind.SEAL: settings.letter_seal_max_chars,
}


class SceneMessageRequest(BaseModel):
    kind: SceneMessageKind = SceneMessageKind.MESSAGE
    text: str = Field(default="", max_length=settings.letter_seal_max_chars)
    current_draft: str = Field(default="", max_length=settings.letter_seal_max_chars)
    verdict: JudgmentVerdict | None = None
    nuance: JudgmentNuance | None = None

    @field_validator("text", "current_draft")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def require_a_valid_verdict_to_pronounce(self) -> Self:
        if self.kind is not SceneMessageKind.PRONOUNCE:
            return self
        if self.verdict is None:
            raise ValueError("a pronouncement needs a verdict")
        if (
            self.nuance is not None
            and self.nuance not in NUANCES_BY_VERDICT[self.verdict]
        ):
            raise ValueError("that nuance does not belong to the verdict")
        return self

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
