from enum import Enum

from app.models.base import WorldModel
from pydantic import Field, model_validator
from strategy_contracts.enums import TroopType
from strategy_contracts.ids import FactionId, Percent, WholeNumber


class MissionTarget(str, Enum):
    COMPOSITION = "composition"
    RESERVES = "reserves"
    PREPARATION = "preparation"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PreparationHint(str, Enum):
    HOLDING = "holding"
    ADVANCING = "advancing"
    FLANKING = "flanking"
    WITHDRAWING = "withdrawing"


class StrengthInterval(WorldModel):
    minimum: WholeNumber
    maximum: WholeNumber

    @model_validator(mode="after")
    def validate_ordered_interval(self) -> "StrengthInterval":
        if self.minimum > self.maximum:
            raise ValueError("strength interval minimum exceeds maximum")
        return self


class ReconReport(WorldModel):
    id: str
    battle_id: str
    observer_faction_id: FactionId
    subject_faction_id: FactionId
    mission_id: str
    target: MissionTarget
    observed_turn: WholeNumber
    observed_exchange: WholeNumber
    available_from_wave: int = Field(ge=1, le=5)
    strength: StrengthInterval
    composition: dict[TroopType, WholeNumber] | None = None
    reserves: StrengthInterval | None = None
    preparation_hint: PreparationHint | None = None
    confidence: Confidence


class ScoutMission(WorldModel):
    id: str
    battle_id: str
    observer_faction_id: FactionId
    subject_faction_id: FactionId
    target: MissionTarget
    execution_turn: WholeNumber
    execution_wave: int = Field(ge=1, le=4)
    briefing_hint: PreparationHint | None = None
    is_resolved: bool = False


class CaptureDecision(str, Enum):
    RELEASE = "release"
    DETAIN = "detain"
    INTERROGATE = "interrogate"


class ScoutCaptureStatus(str, Enum):
    DETAINED = "detained"
    RELEASED = "released"


class ScoutCapture(WorldModel):
    id: str
    battle_id: str
    mission_id: str
    captor_faction_id: FactionId
    origin_faction_id: FactionId
    captured_turn: WholeNumber
    captured_exchange: WholeNumber
    expires_turn: WholeNumber
    mission_target: MissionTarget
    briefing_hint: PreparationHint | None = None
    recon_penalty: Percent = 10
    status: ScoutCaptureStatus = ScoutCaptureStatus.DETAINED
    has_extended: bool = False
    has_decided: bool = False
    has_leaked: bool = False
    decision: CaptureDecision | None = None

    @model_validator(mode="after")
    def validate_expiry(self) -> "ScoutCapture":
        if self.expires_turn <= self.captured_turn:
            raise ValueError("capture expiry must follow capture turn")
        return self


class IntentKind(str, Enum):
    PRESS = "press"
    PRESERVE = "preserve"
    DELAY = "delay"
    WITHDRAW = "withdraw"
    SURRENDER = "surrender"


class IntentSource(str, Enum):
    MODEL = "model"
    FALLBACK = "fallback"


class BattleIntent(WorldModel):
    id: str
    battle_id: str
    faction_id: FactionId
    campaign_turn: WholeNumber
    kind: IntentKind
    source: IntentSource
    input_hash: str
    observation_fingerprint: str
    policy_version: str
    intended_wave: int = Field(ge=1, le=4)
    activation_wave: int = Field(ge=1, le=4)
    activation_exchange: WholeNumber
    request_id: str | None = None
    answer_id: str | None = None
