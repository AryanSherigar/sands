from enum import Enum

from pydantic import Field, model_validator

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import FactionId, WholeNumber
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.terms import VassalTerm

DEFAULT_PRICE_PER_TRIBUTE_PERCENT = 1
DEFAULT_PRICE_PER_LEVY_PERCENT = 1
DEFAULT_PRICE_FOREIGN_POLICY = 15
DEFAULT_PRICE_GARRISON = 10
DEFAULT_PRICE_PER_VASSAL_TURN = 1
DEFAULT_PRICE_FOREVER = 20
DEFAULT_DEMAND_ANSWER_TURNS = 1
DEFAULT_UNREST_PER_EXCESS_DIVISOR = 5
DEFAULT_UNREST_CAP_PER_DEMAND = 30
DEFAULT_GARRISON_UNREST_PER_TURN = 2
DEFAULT_GARRISON_DEMAND_TURNS = 3
DEFAULT_GARRISON_EXCESS_PERCENT = 100
DEFAULT_AXIS_WEIGHT = 4
DEFAULT_OPINION_DIVISOR = 5
DEFAULT_EXCESS_DIVISOR = 10
DEFAULT_STRENGTH_DIVISOR = 10
DEFAULT_ACCEPT_BASE = 40
DEFAULT_COUNTER_BASE = 20
DEFAULT_COUNTER_TARGET_PERCENT = 50
DEFAULT_COUNTER_SPREAD_DIVISOR = 10
DEFAULT_REFUSE_BASE = 10
DEFAULT_STRONG_BASE = 0
DEFAULT_STRONG_MIN_EXCESS_PERCENT = 100
DEFAULT_REBEL_BASE = -10
DEFAULT_REBEL_UNREST_DIVISOR = 2
DEFAULT_REBEL_MIN_POWER_PERCENT = 70
DEFAULT_REBEL_MIN_UNREST = 40
DEFAULT_REFUSE_OPINION_COST = 8
DEFAULT_STRONG_OPINION_COST = 16
DEFAULT_REFUSE_GRIEVANCE = 1
DEFAULT_STRONG_GRIEVANCE = 2
DEFAULT_INDEPENDENCE_WILL_BONUS = 10
DEFAULT_ANNEX_MIN_SCORE = 50
DEFAULT_ANNEX_MIN_STABILITY = 50
DEFAULT_OVERLORD_STRAIN_TREASURY = 50
DEFAULT_OVERLORD_DEMAND_MAX_EXCESS_PERCENT = 50
DEFAULT_DEMAND_COOLDOWN_TURNS = 5
DEFAULT_CONSENT_VALID_TURNS = 3
DEFAULT_OPINION_FADE_PER_TURN = 1


class DemandKind(str, Enum):
    TRIBUTE = "tribute"
    LEVY = "levy"
    GARRISON = "garrison"


class DemandReply(str, Enum):
    ACCEPT = "accept"
    COUNTER = "counter"
    REFUSE = "refuse"
    REFUSE_STRONGLY = "refuse_strongly"
    REBEL = "rebel"


class ConsentAction(str, Enum):
    DECLARE_WAR = "declare_war"
    DEMAND = "demand"
    PACT = "pact"


class VassalTier(str, Enum):
    TRIBUTARY = "tributary"
    CLIENT = "client"
    PUPPET = "puppet"


TIER_PRESETS: dict[VassalTier, dict[str, int | bool]] = {
    VassalTier.TRIBUTARY: {"tribute_share_percent": 20},
    VassalTier.CLIENT: {
        "tribute_share_percent": 30,
        "levy_share_percent": 30,
        "is_foreign_policy_controlled": True,
    },
    VassalTier.PUPPET: {
        "tribute_share_percent": 50,
        "levy_share_percent": FULL_SHARE_PERCENT,
        "is_foreign_policy_controlled": True,
        "has_garrison_rights": True,
    },
}


def tier_term(
    tier: VassalTier,
    overlord_id: FactionId,
    vassal_id: FactionId,
    duration_turns: int = 0,
) -> VassalTerm:
    return VassalTerm(
        overlord_id=overlord_id,
        vassal_id=vassal_id,
        duration_turns=duration_turns,
        **TIER_PRESETS[tier],
    )


class VassalageSetup(StrictModel):
    overlord_id: FactionId
    tribute_share_percent: int = Field(ge=0, le=FULL_SHARE_PERCENT)
    levy_share_percent: int = Field(default=0, ge=0, le=FULL_SHARE_PERCENT)
    is_foreign_policy_controlled: bool = False
    has_garrison_rights: bool = False
    duration_turns: WholeNumber = 0


class VassalTuning(StrictModel):
    rule_version: str = "vassal-v1"
    price_per_tribute_percent: int = Field(
        default=DEFAULT_PRICE_PER_TRIBUTE_PERCENT, ge=0
    )
    price_per_levy_percent: int = Field(default=DEFAULT_PRICE_PER_LEVY_PERCENT, ge=0)
    price_foreign_policy: int = Field(default=DEFAULT_PRICE_FOREIGN_POLICY, ge=0)
    price_garrison: int = Field(default=DEFAULT_PRICE_GARRISON, ge=0)
    price_per_vassal_turn: int = Field(default=DEFAULT_PRICE_PER_VASSAL_TURN, ge=0)
    price_forever: int = Field(default=DEFAULT_PRICE_FOREVER, ge=0)
    demand_answer_turns: int = Field(default=DEFAULT_DEMAND_ANSWER_TURNS, ge=1)
    unrest_per_excess_divisor: int = Field(
        default=DEFAULT_UNREST_PER_EXCESS_DIVISOR, ge=1
    )
    unrest_cap_per_demand: int = Field(default=DEFAULT_UNREST_CAP_PER_DEMAND, ge=0)
    garrison_unrest_per_turn: int = Field(
        default=DEFAULT_GARRISON_UNREST_PER_TURN, ge=0
    )
    garrison_demand_turns: int = Field(default=DEFAULT_GARRISON_DEMAND_TURNS, ge=1)
    garrison_excess_percent: int = Field(default=DEFAULT_GARRISON_EXCESS_PERCENT, ge=1)
    axis_weight: int = Field(default=DEFAULT_AXIS_WEIGHT, ge=0)
    opinion_divisor: int = Field(default=DEFAULT_OPINION_DIVISOR, ge=1)
    excess_divisor: int = Field(default=DEFAULT_EXCESS_DIVISOR, ge=1)
    strength_divisor: int = Field(default=DEFAULT_STRENGTH_DIVISOR, ge=1)
    accept_base: int = DEFAULT_ACCEPT_BASE
    counter_base: int = DEFAULT_COUNTER_BASE
    counter_target_percent: int = Field(default=DEFAULT_COUNTER_TARGET_PERCENT, ge=0)
    counter_spread_divisor: int = Field(default=DEFAULT_COUNTER_SPREAD_DIVISOR, ge=1)
    refuse_base: int = DEFAULT_REFUSE_BASE
    strong_base: int = DEFAULT_STRONG_BASE
    strong_min_excess_percent: int = Field(
        default=DEFAULT_STRONG_MIN_EXCESS_PERCENT, ge=0
    )
    rebel_base: int = DEFAULT_REBEL_BASE
    rebel_unrest_divisor: int = Field(default=DEFAULT_REBEL_UNREST_DIVISOR, ge=1)
    rebel_min_power_percent: int = Field(
        default=DEFAULT_REBEL_MIN_POWER_PERCENT, ge=1, le=FULL_SHARE_PERCENT
    )
    rebel_min_unrest: int = Field(
        default=DEFAULT_REBEL_MIN_UNREST, ge=0, le=FULL_SHARE_PERCENT
    )
    refuse_opinion_cost: int = Field(default=DEFAULT_REFUSE_OPINION_COST, ge=0)
    strong_opinion_cost: int = Field(default=DEFAULT_STRONG_OPINION_COST, ge=0)
    refuse_grievance: int = Field(default=DEFAULT_REFUSE_GRIEVANCE, ge=0)
    strong_grievance: int = Field(default=DEFAULT_STRONG_GRIEVANCE, ge=0)
    independence_will_bonus: int = Field(default=DEFAULT_INDEPENDENCE_WILL_BONUS, ge=0)
    annex_min_score: int = Field(default=DEFAULT_ANNEX_MIN_SCORE, ge=0)
    annex_min_stability: int = Field(default=DEFAULT_ANNEX_MIN_STABILITY, ge=0)
    overlord_strain_treasury: int = Field(
        default=DEFAULT_OVERLORD_STRAIN_TREASURY, ge=0
    )
    overlord_demand_max_excess_percent: int = Field(
        default=DEFAULT_OVERLORD_DEMAND_MAX_EXCESS_PERCENT, ge=1
    )
    demand_cooldown_turns: int = Field(default=DEFAULT_DEMAND_COOLDOWN_TURNS, ge=0)
    consent_valid_turns: int = Field(default=DEFAULT_CONSENT_VALID_TURNS, ge=1)
    opinion_fade_per_turn: int = Field(default=DEFAULT_OPINION_FADE_PER_TURN, ge=0)

    @model_validator(mode="after")
    def validate_strong_refusal_costs_more(self) -> "VassalTuning":
        if self.strong_opinion_cost < self.refuse_opinion_cost:
            raise ValueError("a strong refusal must cost at least a plain refusal")
        return self
