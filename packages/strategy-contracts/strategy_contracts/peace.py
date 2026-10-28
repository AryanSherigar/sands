from enum import Enum

from pydantic import Field, field_validator

from strategy_contracts.base import StrictModel


class PeaceTier(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    GENERATION = "generation"
    PERPETUAL = "perpetual"


FINITE_TIERS = (PeaceTier.SHORT, PeaceTier.MEDIUM, PeaceTier.GENERATION)
DEFAULT_TIER_TURNS: dict[PeaceTier, int] = {
    PeaceTier.SHORT: 6,
    PeaceTier.MEDIUM: 16,
    PeaceTier.GENERATION: 60,
    PeaceTier.PERPETUAL: 0,
}
DEFAULT_TIER_SCORE_COST: dict[PeaceTier, int] = {
    PeaceTier.SHORT: 0,
    PeaceTier.MEDIUM: 5,
    PeaceTier.GENERATION: 15,
    PeaceTier.PERPETUAL: 30,
}
DEFAULT_WHITE_PEACE_SCORE_CEILING = 25
DEFAULT_WHITE_PEACE_MIN_STRAIN = 50
DEFAULT_RANSOM_GOLD_PER_TROOP = 2
DEFAULT_RANSOM_GOLD_PER_CHARACTER = 200
DEFAULT_RANSOM_SCORE_CHIP = 5
DEFAULT_EXCHANGE_SCORE_CHIP = 2
DEFAULT_MEDIATION_ACCEPTANCE_BONUS = 8
DEFAULT_REPUDIATION_COST_PERCENT = 50
DEFAULT_GRIEVANCE_PRESSURE_THRESHOLD = 60
DEFAULT_GRIEVANCE_COOLDOWN_TURNS = 8
DEFAULT_HARSHNESS_WEIGHT = 50
DEFAULT_RECOVERY_WEIGHT = 30
DEFAULT_INTERACTION_WEIGHT = 40
DEFAULT_CEDE_REGION_SCORE_COST = 15
DEFAULT_GOLD_PER_SCORE_POINT = 50
DEFAULT_HOSTAGE_SCORE_VALUE = 3
DEFAULT_PRISONER_SCORE_VALUE = 1
DEFAULT_BROKEN_WILL_CEILING = 20
DEFAULT_ATROCITY_REPUTATION_COST = 20
DEFAULT_HARSHNESS_CAPITAL_BONUS = 40
DEFAULT_HARSHNESS_REGION_PERCENT = 75
DEFAULT_INTERACTION_ALLIANCE_RELIEF = 30
DEFAULT_INTERACTION_TRADE_RELIEF = 30
DEFAULT_INTERACTION_HOSTAGE_RELIEF = 10
DEFAULT_INTERACTION_SHARED_ENEMY_RELIEF = 20
DEFAULT_INTERACTION_OPINION_DIVISOR = 5
PERCENT = 100


def _default_tier_turns() -> dict[PeaceTier, int]:
    return dict(DEFAULT_TIER_TURNS)


def _default_tier_score_cost() -> dict[PeaceTier, int]:
    return dict(DEFAULT_TIER_SCORE_COST)


class PeaceTuning(StrictModel):
    rule_version: str = "peace-v1"
    tier_turns: dict[PeaceTier, int] = Field(default_factory=_default_tier_turns)
    tier_score_cost: dict[PeaceTier, int] = Field(
        default_factory=_default_tier_score_cost
    )
    guarantor_required_from: PeaceTier = PeaceTier.GENERATION
    white_peace_score_ceiling: int = Field(
        default=DEFAULT_WHITE_PEACE_SCORE_CEILING, ge=0, le=PERCENT
    )
    white_peace_min_strain: int = Field(
        default=DEFAULT_WHITE_PEACE_MIN_STRAIN, ge=0, le=PERCENT
    )
    ransom_gold_per_troop: int = Field(default=DEFAULT_RANSOM_GOLD_PER_TROOP, ge=0)
    ransom_gold_per_character: int = Field(
        default=DEFAULT_RANSOM_GOLD_PER_CHARACTER, ge=0
    )
    ransom_score_chip: int = Field(default=DEFAULT_RANSOM_SCORE_CHIP, ge=0)
    exchange_score_chip: int = Field(default=DEFAULT_EXCHANGE_SCORE_CHIP, ge=0)
    mediation_acceptance_bonus: int = Field(
        default=DEFAULT_MEDIATION_ACCEPTANCE_BONUS, ge=0
    )
    renewal_short_tier: PeaceTier = PeaceTier.SHORT
    repudiation_cost_percent: int = Field(
        default=DEFAULT_REPUDIATION_COST_PERCENT, ge=0, le=PERCENT
    )
    cede_region_score_cost: int = Field(default=DEFAULT_CEDE_REGION_SCORE_COST, ge=0)
    gold_per_score_point: int = Field(default=DEFAULT_GOLD_PER_SCORE_POINT, ge=1)
    hostage_score_value: int = Field(default=DEFAULT_HOSTAGE_SCORE_VALUE, ge=0)
    prisoner_score_value: int = Field(default=DEFAULT_PRISONER_SCORE_VALUE, ge=0)
    broken_will_ceiling: int = Field(
        default=DEFAULT_BROKEN_WILL_CEILING, ge=0, le=PERCENT
    )
    atrocity_reputation_cost: int = Field(
        default=DEFAULT_ATROCITY_REPUTATION_COST, ge=0, le=PERCENT
    )
    harshness_capital_bonus: int = Field(
        default=DEFAULT_HARSHNESS_CAPITAL_BONUS, ge=0, le=PERCENT
    )
    harshness_region_percent: int = Field(
        default=DEFAULT_HARSHNESS_REGION_PERCENT, ge=0, le=PERCENT
    )
    interaction_alliance_relief: int = Field(
        default=DEFAULT_INTERACTION_ALLIANCE_RELIEF, ge=0, le=PERCENT
    )
    interaction_trade_relief: int = Field(
        default=DEFAULT_INTERACTION_TRADE_RELIEF, ge=0, le=PERCENT
    )
    interaction_hostage_relief: int = Field(
        default=DEFAULT_INTERACTION_HOSTAGE_RELIEF, ge=0, le=PERCENT
    )
    interaction_shared_enemy_relief: int = Field(
        default=DEFAULT_INTERACTION_SHARED_ENEMY_RELIEF, ge=0, le=PERCENT
    )
    interaction_opinion_divisor: int = Field(
        default=DEFAULT_INTERACTION_OPINION_DIVISOR, ge=1
    )
    harshness_weight: int = Field(default=DEFAULT_HARSHNESS_WEIGHT, ge=0)
    recovery_weight: int = Field(default=DEFAULT_RECOVERY_WEIGHT, ge=0)
    interaction_weight: int = Field(default=DEFAULT_INTERACTION_WEIGHT, ge=0)
    grievance_pressure_threshold: int = Field(
        default=DEFAULT_GRIEVANCE_PRESSURE_THRESHOLD, ge=1, le=PERCENT
    )
    grievance_cooldown_turns: int = Field(
        default=DEFAULT_GRIEVANCE_COOLDOWN_TURNS, ge=1
    )

    @field_validator("tier_turns")
    @classmethod
    def validate_tier_turns(cls, turns: dict[PeaceTier, int]) -> dict[PeaceTier, int]:
        if set(turns) != set(PeaceTier):
            raise ValueError("tier_turns must define every tier")
        finite = [turns[tier] for tier in FINITE_TIERS]
        if finite != sorted(set(finite)) or finite[0] < 1:
            raise ValueError("finite tier lengths must be positive and increasing")
        if turns[PeaceTier.PERPETUAL] != 0:
            raise ValueError("the perpetual tier has no length")
        return turns

    @field_validator("tier_score_cost")
    @classmethod
    def validate_tier_score_cost(
        cls, costs: dict[PeaceTier, int]
    ) -> dict[PeaceTier, int]:
        if set(costs) != set(PeaceTier):
            raise ValueError("tier_score_cost must define every tier")
        ordered = [costs[tier] for tier in PeaceTier]
        if ordered != sorted(set(ordered)) or ordered[0] < 0:
            raise ValueError("tier score costs must be non-negative and increasing")
        return costs
