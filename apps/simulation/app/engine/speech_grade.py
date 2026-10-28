from app.models.world_events import StateChange
from app.models.world_state import WorldState
from strategy_contracts.scene import (
    MAX_SPEECH_MORALE_SWING,
    MAX_SPEECH_RUBRIC_SCORE,
    BattleSpeechOutcome,
    SpeechRubric,
)

CHARACTER_WEIGHT = 2
RUBRIC_WEIGHTS: dict[SpeechRubric, int] = {
    SpeechRubric.ADDRESSES_FEARS: 1,
    SpeechRubric.FITS_RULER_CHARACTER: CHARACTER_WEIGHT,
    SpeechRubric.PROMISES_MADE: 1,
}
MAX_MORALE_PERCENT = 100


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def morale_delta_from_scores(scores: dict[SpeechRubric, int]) -> int:
    """Map weighted rubric scores linearly onto the bounded morale swing."""
    best = MAX_SPEECH_RUBRIC_SCORE * sum(RUBRIC_WEIGHTS.values())
    earned = sum(
        _clamp(scores.get(rubric, 0), 0, MAX_SPEECH_RUBRIC_SCORE) * weight
        for rubric, weight in RUBRIC_WEIGHTS.items()
    )
    span = 2 * MAX_SPEECH_MORALE_SWING
    return _clamp(
        (earned * span) // best - MAX_SPEECH_MORALE_SWING,
        -MAX_SPEECH_MORALE_SWING,
        MAX_SPEECH_MORALE_SWING,
    )


def graded_outcome(scores: dict[SpeechRubric, int]) -> BattleSpeechOutcome:
    return BattleSpeechOutcome(
        morale_delta_percent=morale_delta_from_scores(scores), rubric_scores=scores
    )


def deterministic_fallback_outcome() -> BattleSpeechOutcome:
    return BattleSpeechOutcome(morale_delta_percent=0)


def apply_speech_outcome(
    world: WorldState, army_id: str, outcome: BattleSpeechOutcome
) -> list[StateChange]:
    army = world.armies[army_id]
    morale = _clamp(army.morale + outcome.morale_delta_percent, 0, MAX_MORALE_PERCENT)
    change = StateChange(
        path=f"armies.{army.id}.morale", before=army.morale, after=morale
    )
    army.morale = morale
    return [change]
