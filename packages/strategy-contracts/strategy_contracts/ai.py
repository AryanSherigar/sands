from pydantic import Field

from strategy_contracts.base import StrictModel

DEFAULT_TRAIT_WEIGHT = 1
DEFAULT_STANCE_WEIGHT = 10
DEFAULT_VARIANCE_MARGIN = 5
DEFAULT_MINIMUM_SCORE = 1
DEFAULT_AIM_BONUS = 8
DEFAULT_AIM_MAX_TURNS = 12
DEFAULT_SITUATION_BONUS = 6
DEFAULT_LOW_TREASURY = 50
DEFAULT_LOW_STABILITY = 40
DEFAULT_LOAN_CAP = 200
DEFAULT_MIN_LEVY = 20
DEFAULT_MAX_LEVY = 60
DEFAULT_LEVY_FRICTION = 4
DEFAULT_DISBAND_BELOW_TROOPS = 30
DEFAULT_STRIKE_BONUS = 4
DEFAULT_APPROACH_BONUS = 2
DEFAULT_DEFENSE_BONUS = 6
DEFAULT_RISK_PENALTY = 8
DEFAULT_MERGE_BONUS = 2
DEFAULT_SCOUT_STALE_TURNS = 6
DEFAULT_FEINT_MIN_CUNNING = 2
DEFAULT_FEINT_BONUS = 4
DEFAULT_SUPPLY_STRAINED_PENALTY = 3
DEFAULT_SUPPLY_ISOLATED_PENALTY = 6
DEFAULT_WAR_BASE_BONUS = 4
DEFAULT_GROUND_STRENGTH_DIVISOR = 10
DEFAULT_RATIO_DIVISOR = 20
DEFAULT_SECOND_FRONT_PENALTY = 4
DEFAULT_DEMAND_GOLD = 30
DEFAULT_DEMAND_MIN_RATIO = 120
DEFAULT_AIM_TARGET_BONUS = 4
DEFAULT_FORGERY_BONUS = 2
DEFAULT_UPRISING_BONUS = 10
DEFAULT_MAX_ARMIES = 6


class AiTuning(StrictModel):
    rule_version: str = "ai-v1"
    trait_weight: int = Field(default=DEFAULT_TRAIT_WEIGHT, ge=0)
    stance_weight: int = Field(default=DEFAULT_STANCE_WEIGHT, ge=0)
    variance_margin: int = Field(default=DEFAULT_VARIANCE_MARGIN, ge=0)
    minimum_score: int = Field(default=DEFAULT_MINIMUM_SCORE, ge=0)
    aim_bonus: int = Field(default=DEFAULT_AIM_BONUS, ge=0)
    aim_max_turns: int = Field(default=DEFAULT_AIM_MAX_TURNS, ge=1)
    situation_bonus: int = Field(default=DEFAULT_SITUATION_BONUS, ge=0)
    low_treasury: int = Field(default=DEFAULT_LOW_TREASURY, ge=0)
    low_stability: int = Field(default=DEFAULT_LOW_STABILITY, ge=0)
    loan_cap: int = Field(default=DEFAULT_LOAN_CAP, ge=0)
    min_levy: int = Field(default=DEFAULT_MIN_LEVY, ge=1)
    max_levy: int = Field(default=DEFAULT_MAX_LEVY, ge=1)
    levy_friction: int = Field(default=DEFAULT_LEVY_FRICTION, ge=0)
    disband_below_troops: int = Field(default=DEFAULT_DISBAND_BELOW_TROOPS, ge=0)
    strike_bonus: int = Field(default=DEFAULT_STRIKE_BONUS, ge=0)
    approach_bonus: int = Field(default=DEFAULT_APPROACH_BONUS, ge=0)
    defense_bonus: int = Field(default=DEFAULT_DEFENSE_BONUS, ge=0)
    risk_penalty: int = Field(default=DEFAULT_RISK_PENALTY, ge=0)
    merge_bonus: int = Field(default=DEFAULT_MERGE_BONUS, ge=0)
    scout_stale_turns: int = Field(default=DEFAULT_SCOUT_STALE_TURNS, ge=1)
    feint_min_cunning: int = DEFAULT_FEINT_MIN_CUNNING
    feint_bonus: int = Field(default=DEFAULT_FEINT_BONUS, ge=0)
    supply_strained_penalty: int = Field(default=DEFAULT_SUPPLY_STRAINED_PENALTY, ge=0)
    supply_isolated_penalty: int = Field(default=DEFAULT_SUPPLY_ISOLATED_PENALTY, ge=0)
    war_base_bonus: int = Field(default=DEFAULT_WAR_BASE_BONUS, ge=0)
    ground_strength_divisor: int = Field(default=DEFAULT_GROUND_STRENGTH_DIVISOR, ge=1)
    ratio_divisor: int = Field(default=DEFAULT_RATIO_DIVISOR, ge=1)
    second_front_penalty: int = Field(default=DEFAULT_SECOND_FRONT_PENALTY, ge=0)
    demand_gold: int = Field(default=DEFAULT_DEMAND_GOLD, ge=0)
    demand_min_ratio: int = Field(default=DEFAULT_DEMAND_MIN_RATIO, ge=0)
    aim_target_bonus: int = Field(default=DEFAULT_AIM_TARGET_BONUS, ge=0)
    forgery_bonus: int = Field(default=DEFAULT_FORGERY_BONUS, ge=0)
    uprising_bonus: int = Field(default=DEFAULT_UPRISING_BONUS, ge=0)
    max_armies: int = Field(default=DEFAULT_MAX_ARMIES, ge=1)
