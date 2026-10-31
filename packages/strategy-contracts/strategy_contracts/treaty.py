from enum import Enum

from pydantic import Field

from strategy_contracts.base import StrictModel

DEFAULT_TRADE_VALUE_PER_TURN = 4
DEFAULT_TRADE_INCOME_PERCENT = 10
DEFAULT_ACCESS_VALUE_PER_TURN = 2
DEFAULT_CONDITIONAL_TRIGGER_PERCENT = 60
DEFAULT_CONDITIONAL_GATE_PERCENT = 100
MAX_CONDITIONAL_PERCENT = 200


class Verdict(str, Enum):
    ACCEPT = "accept"
    HAGGLE = "haggle"
    REFUSE = "refuse"


class WeightBand(str, Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"


class TreatyTuning(StrictModel):
    trade_value_per_turn: int = Field(default=DEFAULT_TRADE_VALUE_PER_TURN, ge=1)
    trade_income_percent: int = Field(default=DEFAULT_TRADE_INCOME_PERCENT, ge=1)
    access_value_per_turn: int = Field(default=DEFAULT_ACCESS_VALUE_PER_TURN, ge=1)
    conditional_trigger_percent: int = Field(
        default=DEFAULT_CONDITIONAL_TRIGGER_PERCENT, ge=0, le=MAX_CONDITIONAL_PERCENT
    )
    conditional_gate_percent: int = Field(
        default=DEFAULT_CONDITIONAL_GATE_PERCENT, ge=0, le=MAX_CONDITIONAL_PERCENT
    )
