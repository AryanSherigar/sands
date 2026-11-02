from enum import StrEnum

from pydantic import Field

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import WholeNumber

DEFAULT_COOLDOWN_TURNS = 4
DEFAULT_PEACE_OFFER_MIN_STRAIN = 60
DEFAULT_PEACE_OFFER_MAX_WILL = 40
DEFAULT_DEMAND_MIN_SCORE_EDGE = 30
DEFAULT_IGNORE_OPINION_PENALTY = 5
DEFAULT_IGNORE_OUTRAGE_LEVELS = 1
DEFAULT_TALKS_MIN_WAR_TURNS = 3
DEFAULT_INTENSIFY_GROUND_STRENGTH = 10
DEFAULT_OATH_OFFER_MIN_OPINION = 20
DEFAULT_OATH_OFFER_DURATION_TURNS = 12


class OvertureKind(StrEnum):
    PEACE_OFFER = "peace_offer"
    DEMAND = "demand"
    CALL_FOR_TALKS = "call_for_talks"
    HEIR_RENEWAL = "heir_renewal"
    RANSOM_DEMAND = "ransom_demand"
    RANSOM_COUNTER = "ransom_counter"
    OATH_OFFER = "oath_offer"


class OvertureTuning(StrictModel):
    cooldown_turns: int = Field(default=DEFAULT_COOLDOWN_TURNS, ge=1)
    peace_offer_min_strain: WholeNumber = DEFAULT_PEACE_OFFER_MIN_STRAIN
    peace_offer_max_will: WholeNumber = DEFAULT_PEACE_OFFER_MAX_WILL
    demand_min_score_edge: WholeNumber = DEFAULT_DEMAND_MIN_SCORE_EDGE
    ignore_opinion_penalty: WholeNumber = DEFAULT_IGNORE_OPINION_PENALTY
    ignore_outrage_levels: WholeNumber = DEFAULT_IGNORE_OUTRAGE_LEVELS
    talks_min_war_turns: WholeNumber = DEFAULT_TALKS_MIN_WAR_TURNS
    intensify_ground_strength: WholeNumber = DEFAULT_INTENSIFY_GROUND_STRENGTH
    oath_offer_min_opinion: WholeNumber = DEFAULT_OATH_OFFER_MIN_OPINION
    oath_offer_duration_turns: int = Field(
        default=DEFAULT_OATH_OFFER_DURATION_TURNS, ge=1
    )
