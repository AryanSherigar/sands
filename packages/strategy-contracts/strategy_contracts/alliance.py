from enum import Enum

from pydantic import Field, model_validator

from strategy_contracts.base import StrictModel

DEFAULT_CALL_ANSWER_TURNS = 1
DEFAULT_REFUSAL_COST_OFFENSIVE = 5
DEFAULT_REFUSAL_COST_DEFENSIVE = 10
DEFAULT_REFUSALS_TO_BREAK = 2
DEFAULT_DENOUNCE_OPINION_COST = 8
DEFAULT_BOTH_SIDES_OPINION_COST = 6
DEFAULT_JOIN_THRESHOLD = 0
DEFAULT_JOIN_AXIS_WEIGHT = 5
DEFAULT_JOIN_OPINION_DIVISOR = 4
DEFAULT_JOIN_STRENGTH_DIVISOR = 10
DEFAULT_JOIN_DEFENSIVE_BONUS = 5
DEFAULT_JOIN_GROUND_BONUS = 5
DEFAULT_OPINION_FADE_PER_TURN = 1
DEFAULT_PRICE_PER_ALLIANCE_TURN = 1
DEFAULT_PRICE_FOREVER = 20
DEFAULT_PRICE_OFFENSIVE_EXTRA = 5
DEFAULT_PRICE_NO_SEPARATE_PEACE_EXTRA = 5


class AllianceType(str, Enum):
    DEFENSIVE = "defensive"
    OFFENSIVE = "offensive"


class AllianceTuning(StrictModel):
    rule_version: str = "alliance-v1"
    call_answer_turns: int = Field(default=DEFAULT_CALL_ANSWER_TURNS, ge=1)
    refusal_opinion_cost_offensive: int = Field(
        default=DEFAULT_REFUSAL_COST_OFFENSIVE, ge=0
    )
    refusal_opinion_cost_defensive: int = Field(
        default=DEFAULT_REFUSAL_COST_DEFENSIVE, ge=0
    )
    refusal_breaks_alliance_after: int = Field(default=DEFAULT_REFUSALS_TO_BREAK, ge=1)
    is_destruction_refusal_breaking: bool = True
    denounce_opinion_cost: int = Field(default=DEFAULT_DENOUNCE_OPINION_COST, ge=0)
    both_sides_opinion_cost: int = Field(default=DEFAULT_BOTH_SIDES_OPINION_COST, ge=0)
    join_threshold: int = DEFAULT_JOIN_THRESHOLD
    join_axis_weight: int = Field(default=DEFAULT_JOIN_AXIS_WEIGHT, ge=0)
    join_opinion_divisor: int = Field(default=DEFAULT_JOIN_OPINION_DIVISOR, ge=1)
    join_strength_divisor: int = Field(default=DEFAULT_JOIN_STRENGTH_DIVISOR, ge=1)
    join_defensive_bonus: int = Field(default=DEFAULT_JOIN_DEFENSIVE_BONUS, ge=0)
    join_ground_bonus: int = Field(default=DEFAULT_JOIN_GROUND_BONUS, ge=0)
    opinion_fade_per_turn: int = Field(default=DEFAULT_OPINION_FADE_PER_TURN, ge=0)
    price_per_alliance_turn: int = Field(default=DEFAULT_PRICE_PER_ALLIANCE_TURN, ge=0)
    price_forever: int = Field(default=DEFAULT_PRICE_FOREVER, ge=0)
    price_offensive_extra: int = Field(default=DEFAULT_PRICE_OFFENSIVE_EXTRA, ge=0)
    price_no_separate_peace_extra: int = Field(
        default=DEFAULT_PRICE_NO_SEPARATE_PEACE_EXTRA, ge=0
    )

    @model_validator(mode="after")
    def validate_defensive_refusal_costs_more(self) -> "AllianceTuning":
        if self.refusal_opinion_cost_defensive <= self.refusal_opinion_cost_offensive:
            raise ValueError("refusing a defensive call must cost more opinion")
        return self
