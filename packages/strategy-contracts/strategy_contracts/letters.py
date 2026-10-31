from enum import StrEnum

from pydantic import Field

from strategy_contracts.base import StrictModel

DEFAULT_LETTER_COOLDOWN_TURNS = 6


class LetterTopic(StrEnum):
    COURTESY = "courtesy"
    WARNING = "warning"
    BORDER_DISPUTE = "border_dispute"


class LetterTuning(StrictModel):
    is_enabled: bool = False
    cooldown_turns: int = Field(default=DEFAULT_LETTER_COOLDOWN_TURNS, ge=1)
