from typing import Annotated, Literal

from pydantic import Field

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import RegionId, WholeNumber
from strategy_contracts.limits import FULL_SHARE_PERCENT

DEFAULT_CONQUEST_WINDOW_TURNS = 3
DEFAULT_CONQUEST_WEALTH_DIVISOR = 2
DEFAULT_CONQUEST_REPUTATION_COST = 5
DEFAULT_OATHBREAKER_THREAT = 15
DEFAULT_NO_GROUND_WAR_THREAT = 10
DEFAULT_ATROCITY_THREAT = 8
DEFAULT_BALANCE_FAIR_SHARE_PERCENT = 30
DEFAULT_BALANCE_WEIGHT_PERCENT = 100
DEFAULT_HOARD_FAIR_SHARE_PERCENT = 35
DEFAULT_HOARD_WEIGHT_PERCENT = 150
DEFAULT_HOARD_FREE_GOLD = 250
DEFAULT_HOARD_GOLD_PER_POINT = 20
DEFAULT_HOARD_PRETEXT_THREAT = 25
DEFAULT_JOIN_THREAT = 40
DEFAULT_JOIN_OPINION_BELOW = 0
DEFAULT_CAUTION_SHIFT = 5
DEFAULT_PRIDE_SHIFT = 5
DEFAULT_END_THREAT = 25
DEFAULT_MIN_MEMBERS = 2
DEFAULT_DURATION_TURNS = 10
DEFAULT_MEMBER_OPINION_PENALTY = 15
DEFAULT_PEACE_SHIFT = 10
DEFAULT_APPEASE_BASE_PRICE = 20
DEFAULT_APPEASE_OPINION_WEIGHT = 2
DEFAULT_APPEASE_CAUTION_DISCOUNT = 2
DEFAULT_APPEASE_PRIDE_SURCHARGE = 2
DEFAULT_APPEASE_GOLD_VALUE_PERCENT = 100
DEFAULT_APPEASE_PACT_VALUE_PER_TURN = 3
DEFAULT_APPEASE_PACT_MAX_VALUE = 30
DEFAULT_APPEASE_CESSION_VALUE_DIVISOR = 1
DEFAULT_APPEASE_COOLDOWN_TURNS = 3
DEFAULT_APPEASE_REJOIN_LOCKOUT_TURNS = 5
DEFAULT_APPEASE_MAX_PACT_TURNS = 12


class CoalitionTuning(StrictModel):
    rule_version: int = Field(default=1, ge=1)
    conquest_window_turns: int = Field(default=DEFAULT_CONQUEST_WINDOW_TURNS, ge=1)
    conquest_wealth_divisor: int = Field(default=DEFAULT_CONQUEST_WEALTH_DIVISOR, ge=1)
    conquest_reputation_cost: WholeNumber = DEFAULT_CONQUEST_REPUTATION_COST
    oathbreaker_threat: WholeNumber = DEFAULT_OATHBREAKER_THREAT
    no_ground_war_threat: WholeNumber = DEFAULT_NO_GROUND_WAR_THREAT
    atrocity_threat: WholeNumber = DEFAULT_ATROCITY_THREAT
    balance_fair_share_percent: int = Field(
        default=DEFAULT_BALANCE_FAIR_SHARE_PERCENT, ge=0, le=FULL_SHARE_PERCENT
    )
    balance_weight_percent: WholeNumber = DEFAULT_BALANCE_WEIGHT_PERCENT
    hoard_fair_share_percent: int = Field(
        default=DEFAULT_HOARD_FAIR_SHARE_PERCENT, ge=0, le=FULL_SHARE_PERCENT
    )
    hoard_weight_percent: WholeNumber = DEFAULT_HOARD_WEIGHT_PERCENT
    hoard_free_gold: WholeNumber = DEFAULT_HOARD_FREE_GOLD
    hoard_gold_per_point: int = Field(default=DEFAULT_HOARD_GOLD_PER_POINT, ge=1)
    hoard_pretext_threat: WholeNumber = DEFAULT_HOARD_PRETEXT_THREAT
    join_threat: WholeNumber = DEFAULT_JOIN_THREAT
    join_opinion_below: int = DEFAULT_JOIN_OPINION_BELOW
    caution_shift: WholeNumber = DEFAULT_CAUTION_SHIFT
    pride_shift: WholeNumber = DEFAULT_PRIDE_SHIFT
    end_threat: WholeNumber = DEFAULT_END_THREAT
    min_members: int = Field(default=DEFAULT_MIN_MEMBERS, ge=2)
    duration_turns: int = Field(default=DEFAULT_DURATION_TURNS, ge=1)
    member_opinion_penalty: WholeNumber = DEFAULT_MEMBER_OPINION_PENALTY
    peace_shift: WholeNumber = DEFAULT_PEACE_SHIFT
    appease_base_price: WholeNumber = DEFAULT_APPEASE_BASE_PRICE
    appease_opinion_weight: WholeNumber = DEFAULT_APPEASE_OPINION_WEIGHT
    appease_caution_discount: WholeNumber = DEFAULT_APPEASE_CAUTION_DISCOUNT
    appease_pride_surcharge: WholeNumber = DEFAULT_APPEASE_PRIDE_SURCHARGE
    appease_gold_value_percent: WholeNumber = DEFAULT_APPEASE_GOLD_VALUE_PERCENT
    appease_pact_value_per_turn: WholeNumber = DEFAULT_APPEASE_PACT_VALUE_PER_TURN
    appease_pact_max_value: WholeNumber = DEFAULT_APPEASE_PACT_MAX_VALUE
    appease_cession_value_divisor: int = Field(
        default=DEFAULT_APPEASE_CESSION_VALUE_DIVISOR, ge=1
    )
    appease_cooldown_turns: int = Field(default=DEFAULT_APPEASE_COOLDOWN_TURNS, ge=1)
    appease_rejoin_lockout_turns: int = Field(
        default=DEFAULT_APPEASE_REJOIN_LOCKOUT_TURNS, ge=1
    )
    appease_max_pact_turns: int = Field(default=DEFAULT_APPEASE_MAX_PACT_TURNS, ge=1)


class GoldOffer(StrictModel):
    kind: Literal["gold"] = "gold"
    amount: int = Field(ge=1)


class PactOffer(StrictModel):
    kind: Literal["pact"] = "pact"
    duration_turns: int = Field(ge=1)


class ClaimCessionOffer(StrictModel):
    kind: Literal["claim_cession"] = "claim_cession"
    region_id: RegionId


AppeaseOffer = Annotated[
    GoldOffer | PactOffer | ClaimCessionOffer, Field(discriminator="kind")
]
