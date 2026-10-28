from enum import Enum

from pydantic import Field, model_validator

from strategy_contracts.base import StrictModel


class GroundKind(str, Enum):
    CLAIM = "claim"
    BROKEN_PROMISE = "broken_promise"
    INSULT = "insult"
    HOLY_WAR = "holy_war"
    REFUSED_DEMAND = "refused_demand"
    INDEPENDENCE = "independence"


class ScoreSource(str, Enum):
    BATTLE_WON = "battle_won"
    ARMY_DESTROYED = "army_destroyed"
    PRISONERS_HELD = "prisoners_held"
    REGION_OCCUPIED = "region_occupied"
    CAPITAL_OR_FORTRESS = "capital_or_fortress"
    RAIDING = "raiding"
    ALLY_DEFECTED = "ally_defected"
    RANSOMED_NOTABLE = "ransomed_notable"


DEFAULT_WAR_SCORE_CAP = 100
DEFAULT_GOAL_SLOT_THRESHOLDS = (40, 70)
DEFAULT_SCORE_WEIGHTS: dict[ScoreSource, int] = {
    ScoreSource.BATTLE_WON: 15,
    ScoreSource.ARMY_DESTROYED: 10,
    ScoreSource.PRISONERS_HELD: 1,
    ScoreSource.REGION_OCCUPIED: 20,
    ScoreSource.CAPITAL_OR_FORTRESS: 30,
    ScoreSource.RAIDING: 10,
    ScoreSource.ALLY_DEFECTED: 15,
    ScoreSource.RANSOMED_NOTABLE: 5,
}
DEFAULT_GROUND_BASE_STRENGTH: dict[GroundKind, int] = {
    GroundKind.CLAIM: 100,
    GroundKind.BROKEN_PROMISE: 80,
    GroundKind.INSULT: 20,
    GroundKind.HOLY_WAR: 60,
    GroundKind.REFUSED_DEMAND: 70,
    GroundKind.INDEPENDENCE: 100,
}


def _default_goal_slot_thresholds() -> list[int]:
    return list(DEFAULT_GOAL_SLOT_THRESHOLDS)


def _default_score_weights() -> dict[ScoreSource, int]:
    return dict(DEFAULT_SCORE_WEIGHTS)


def _default_ground_base_strength() -> dict[GroundKind, int]:
    return dict(DEFAULT_GROUND_BASE_STRENGTH)


class DiplomacyTuning(StrictModel):
    rule_version: str = "diplomacy-v1"
    war_score_cap: int = Field(default=DEFAULT_WAR_SCORE_CAP, ge=1)
    goal_slot_thresholds: list[int] = Field(
        default_factory=_default_goal_slot_thresholds
    )
    score_weights: dict[ScoreSource, int] = Field(
        default_factory=_default_score_weights
    )
    prisoners_per_score_point: int = Field(default=50, ge=1)
    ground_base_strength: dict[GroundKind, int] = Field(
        default_factory=_default_ground_base_strength
    )
    act_threshold_base: int = Field(default=50, ge=0)
    act_threshold_min: int = Field(default=20, ge=0)
    act_threshold_max: int = Field(default=80, ge=0)
    act_threshold_step: int = Field(default=5, ge=0)
    fade_base: int = Field(default=2, ge=0)
    fade_min: int = Field(default=1, ge=0)
    fade_max: int = Field(default=4, ge=0)
    fade_axis_divisor: int = Field(default=3, ge=1)
    heir_claim_percent: int = Field(default=50, ge=0, le=100)
    heir_insult_percent: int = Field(default=25, ge=0, le=100)
    max_insult_grade: int = Field(default=4, ge=0)
    insult_strength_cap_per_turn: int = Field(default=40, ge=0)
    wealthy_region_wealth: int = Field(default=100, ge=0)
    no_ground_reputation_cost: int = Field(default=20, ge=0)
    no_ground_stability_cost: int = Field(default=10, ge=0)
    surprise_reputation_cost: int = Field(default=5, ge=0)
    breach_reputation_cost: int = Field(default=15, ge=0)
    breach_stability_cost: int = Field(default=10, ge=0)
    warning_window_turns: int = Field(default=3, ge=0)
    reparations_gold: int = Field(default=100, ge=0)
    fabrication_turns: int = Field(default=3, ge=1)
    fabricated_claim_strength: int = Field(default=70, ge=0)
    suspect_per_turn: int = Field(default=15, ge=0)
    exposure_chance_cap_percent: int = Field(default=80, ge=0, le=100)
    exposure_chance_divisor: int = Field(default=4, ge=1)
    exposure_reputation_cost: int = Field(default=15, ge=0)
    demand_base_limit_percent: int = Field(default=20, ge=0)
    demand_axis_step: int = Field(default=5, ge=0)
    demand_leverage_divisor: int = Field(default=5, ge=1)
    demand_limit_max_percent: int = Field(default=60, ge=0, le=100)
    talks_refusal_warmth: int = -20

    @model_validator(mode="after")
    def validate_ordered_bounds(self) -> "DiplomacyTuning":
        if (
            not self.act_threshold_min
            <= self.act_threshold_base
            <= self.act_threshold_max
        ):
            raise ValueError("act threshold must sit between its minimum and maximum")
        if not self.fade_min <= self.fade_base <= self.fade_max:
            raise ValueError("fade base must sit between its minimum and maximum")
        if self.goal_slot_thresholds != sorted(self.goal_slot_thresholds):
            raise ValueError("goal slot thresholds must be ascending")
        return self
