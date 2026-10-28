from pydantic import Field, field_validator

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import WholeNumber
from strategy_contracts.scene import MAX_TONE_GRADE, OutrageLevel

RAISED_LEVEL_COUNT = len(OutrageLevel) - 1
DEFAULT_LEVEL_THRESHOLDS_PERCENT = [25, 50, 100, 150]
DEFAULT_MIN_DEMANDER_SCORE = 10
DEFAULT_TRAIT_SHIFT_TOTAL = 3
DEFAULT_TONE_WORSEN_AT = 4
DEFAULT_TONE_SOFTEN_AT = 1
DEFAULT_MOBILIZATION_TURNS = 4
DEFAULT_ENRAGED_TURNS = 3
DEFAULT_MOBILIZATION_ORDERS_BONUS = 1
DEFAULT_MOBILIZATION_STABILITY_LOSS = 2
DEFAULT_MOBILIZATION_UNREST = 5
DEFAULT_MOBILIZATION_EXHAUSTION = 2
DEFAULT_MOBILIZATION_WILL = 15
DEFAULT_MOBILIZATION_STRAIN = 10
DEFAULT_HUMILIATION_PER_LEVEL = 5
DEFAULT_HUMILIATION_SHIFT_DIVISOR = 5
DEFAULT_NO_QUARTER_MORALE_BONUS = 10
DEFAULT_PRESS_TRAIT_TOTAL = 3
DEFAULT_AI_ATTACK_BOOST = 20
DEFAULT_AI_DEFENSE_PENALTY = 15
DEFAULT_AI_CALCULATING_CUNNING = 3


def _default_level_thresholds() -> list[int]:
    return list(DEFAULT_LEVEL_THRESHOLDS_PERCENT)


class OutrageTuning(StrictModel):
    rule_version: int = Field(default=1, ge=1)
    level_thresholds_percent: list[int] = Field(
        default_factory=_default_level_thresholds
    )
    min_demander_score: int = Field(default=DEFAULT_MIN_DEMANDER_SCORE, ge=1)
    trait_shift_total: int = Field(default=DEFAULT_TRAIT_SHIFT_TOTAL, ge=1)
    tone_worsen_at: int = Field(default=DEFAULT_TONE_WORSEN_AT, ge=0, le=MAX_TONE_GRADE)
    tone_soften_at: int = Field(default=DEFAULT_TONE_SOFTEN_AT, ge=0, le=MAX_TONE_GRADE)
    mobilization_turns: int = Field(default=DEFAULT_MOBILIZATION_TURNS, ge=1)
    enraged_turns: int = Field(default=DEFAULT_ENRAGED_TURNS, ge=1)
    mobilization_orders_bonus: WholeNumber = DEFAULT_MOBILIZATION_ORDERS_BONUS
    mobilization_stability_loss: WholeNumber = DEFAULT_MOBILIZATION_STABILITY_LOSS
    mobilization_unrest: WholeNumber = DEFAULT_MOBILIZATION_UNREST
    mobilization_exhaustion: WholeNumber = DEFAULT_MOBILIZATION_EXHAUSTION
    mobilization_will: WholeNumber = DEFAULT_MOBILIZATION_WILL
    mobilization_strain: WholeNumber = DEFAULT_MOBILIZATION_STRAIN
    humiliation_per_level: WholeNumber = DEFAULT_HUMILIATION_PER_LEVEL
    humiliation_shift_divisor: int = Field(
        default=DEFAULT_HUMILIATION_SHIFT_DIVISOR, ge=1
    )
    no_quarter_morale_bonus: WholeNumber = DEFAULT_NO_QUARTER_MORALE_BONUS
    press_trait_total: int = Field(default=DEFAULT_PRESS_TRAIT_TOTAL, ge=1)
    ai_attack_boost: WholeNumber = DEFAULT_AI_ATTACK_BOOST
    ai_defense_penalty: WholeNumber = DEFAULT_AI_DEFENSE_PENALTY
    ai_calculating_cunning: int = Field(default=DEFAULT_AI_CALCULATING_CUNNING, ge=1)

    @field_validator("level_thresholds_percent")
    @classmethod
    def validate_level_thresholds(cls, thresholds: list[int]) -> list[int]:
        if len(thresholds) != RAISED_LEVEL_COUNT:
            raise ValueError(
                "level_thresholds_percent needs one entry per raised level"
            )
        if thresholds != sorted(set(thresholds)):
            raise ValueError("level_thresholds_percent must be strictly increasing")
        return thresholds
