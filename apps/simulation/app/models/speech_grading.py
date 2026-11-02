from app.models.base import WorldModel
from pydantic import Field, field_validator
from strategy_contracts.battle_speech import MAX_SPEECH_TALKS, ArmyMood
from strategy_contracts.limits import MAX_NAME_CHARS, MAX_TEXT_CHARS

MAX_RULER_NOTES = 3
MAX_RULER_AMBITIONS = 2


def _require_bounded_talks(talks: list[str]) -> list[str]:
    if any(len(talk) > MAX_TEXT_CHARS for talk in talks):
        raise ValueError("a talk exceeds the text limit")
    return talks


class SpeechBriefing(WorldModel):
    talks: list[str] = Field(min_length=1, max_length=MAX_SPEECH_TALKS)
    ruler_name: str = Field(max_length=MAX_NAME_CHARS)
    ruler_epithet: str | None = None
    ruler_trait_notes: list[str] = Field(max_length=MAX_RULER_NOTES)
    ruler_ambitions: list[str] = Field(max_length=MAX_RULER_AMBITIONS)
    troop_count: int = Field(ge=0)
    army_morale: int = Field(ge=0, le=100)
    army_fatigue: int = Field(ge=0, le=100)
    unpaid_turns: int = Field(ge=0)

    _bounded_talks = field_validator("talks")(_require_bounded_talks)


class MoodBriefing(WorldModel):
    talks: list[str] = Field(min_length=1, max_length=MAX_SPEECH_TALKS)
    ruler_name: str = Field(max_length=MAX_NAME_CHARS)
    ruler_trait_notes: list[str] = Field(max_length=MAX_RULER_NOTES)
    army_mood: ArmyMood

    _bounded_talks = field_validator("talks")(_require_bounded_talks)
