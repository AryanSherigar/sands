from enum import Enum

from pydantic import Field

from strategy_contracts.base import StrictModel

MAX_SPEECH_TALKS = 3
MIN_REACTION_INTENSITY = 1
MAX_REACTION_INTENSITY = 3


class CrowdMood(str, Enum):
    HUSH = "hush"
    MURMUR = "murmur"
    PROTEST = "protest"
    CHEER = "cheer"


class CrowdReaction(StrictModel):
    mood: CrowdMood
    intensity: int = Field(ge=MIN_REACTION_INTENSITY, le=MAX_REACTION_INTENSITY)


class MoraleBucket(str, Enum):
    BROKEN = "broken"
    SHAKEN = "shaken"
    STEADY = "steady"
    RESOLUTE = "resolute"
    FERVENT = "fervent"


class ExhaustionBucket(str, Enum):
    FRESH = "fresh"
    TIRED = "tired"
    SPENT = "spent"


class PayBucket(str, Enum):
    PAID = "paid"
    GRUMBLING = "grumbling"
    UNPAID = "unpaid"


class ArmyMood(StrictModel):
    morale: MoraleBucket
    exhaustion: ExhaustionBucket
    pay: PayBucket
