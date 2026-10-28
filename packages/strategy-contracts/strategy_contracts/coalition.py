from pydantic import Field

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import WholeNumber
from strategy_contracts.limits import FULL_SHARE_PERCENT

DEFAULT_CONQUEST_WINDOW_TURNS = 3
DEFAULT_CONQUEST_WEALTH_DIVISOR = 2
DEFAULT_CONQUEST_REPUTATION_COST = 5
DEFAULT_OATHBREAKER_THREAT = 15
DEFAULT_NO_GROUND_WAR_THREAT = 10
DEFAULT_ATROCITY_THREAT = 8
DEFAULT_BALANCE_FAIR_SHARE_PERCENT = 30
DEFAULT_BALANCE_WEIGHT_PERCENT = 100
DEFAULT_JOIN_THREAT = 40
DEFAULT_JOIN_OPINION_BELOW = 0
DEFAULT_CAUTION_SHIFT = 5
DEFAULT_PRIDE_SHIFT = 5
DEFAULT_END_THREAT = 25
DEFAULT_MIN_MEMBERS = 2
DEFAULT_DURATION_TURNS = 10
DEFAULT_MEMBER_OPINION_PENALTY = 15
DEFAULT_PEACE_SHIFT = 10


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
    join_threat: WholeNumber = DEFAULT_JOIN_THREAT
    join_opinion_below: int = DEFAULT_JOIN_OPINION_BELOW
    caution_shift: WholeNumber = DEFAULT_CAUTION_SHIFT
    pride_shift: WholeNumber = DEFAULT_PRIDE_SHIFT
    end_threat: WholeNumber = DEFAULT_END_THREAT
    min_members: int = Field(default=DEFAULT_MIN_MEMBERS, ge=2)
    duration_turns: int = Field(default=DEFAULT_DURATION_TURNS, ge=1)
    member_opinion_penalty: WholeNumber = DEFAULT_MEMBER_OPINION_PENALTY
    peace_shift: WholeNumber = DEFAULT_PEACE_SHIFT
