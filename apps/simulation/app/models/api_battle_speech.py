from app.models.base import WorldModel
from app.models.battle_progress import MutationResponse, OperationGuard
from app.models.world_battle import BattleSpeechStatus
from pydantic import Field, field_validator
from strategy_contracts.battle_speech import MAX_SPEECH_TALKS, ArmyMood, CrowdReaction
from strategy_contracts.limits import MAX_TEXT_CHARS
from strategy_contracts.scene import BattleSpeechOutcome


class SpeechView(WorldModel):
    status: BattleSpeechStatus
    officer_report: str
    mood: ArmyMood
    next_talk: int | None
    reactions: list[CrowdReaction]
    outcome: BattleSpeechOutcome | None = None


class SpeechTalkRequest(WorldModel):
    guard: OperationGuard
    talk_index: int = Field(ge=1, le=MAX_SPEECH_TALKS)
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)

    @field_validator("text")
    @classmethod
    def validate_text_is_not_blank(cls, text: str) -> str:
        if not text.strip():
            raise ValueError("a talk cannot be blank")
        return text


class SpeechTalkResult(WorldModel):
    reaction: CrowdReaction
    is_complete: bool
    morale_delta_percent: int | None
    state: MutationResponse
