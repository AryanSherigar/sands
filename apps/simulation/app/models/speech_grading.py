from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.ids import ArmyId
from strategy_contracts.limits import MAX_NAME_CHARS, MAX_TEXT_CHARS

MAX_RULER_NOTES = 3
MAX_RULER_AMBITIONS = 2


class SpeechGradeRequest(WorldModel):
    army_id: ArmyId
    speech_text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)


class SpeechBriefing(WorldModel):
    speech_text: str = Field(max_length=MAX_TEXT_CHARS)
    ruler_name: str = Field(max_length=MAX_NAME_CHARS)
    ruler_epithet: str | None = None
    ruler_trait_notes: list[str] = Field(max_length=MAX_RULER_NOTES)
    ruler_ambitions: list[str] = Field(max_length=MAX_RULER_AMBITIONS)
    troop_count: int = Field(ge=0)
    army_morale: int = Field(ge=0, le=100)
    army_fatigue: int = Field(ge=0, le=100)
    unpaid_turns: int = Field(ge=0)
