from pydantic import Field

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import Percent

DEFAULT_FULL_PROGRESS = 100
DEFAULT_TROOP_FACTOR = 10
DEFAULT_GARRISON_FLOOR = 100
DEFAULT_MIN_STEP = 5
DEFAULT_HOLD_DELAY = 3
DEFAULT_CONQUEST_UNREST = 20


class SiegeTuning(StrictModel):
    """Sieges and occupation: progress per turn, hold before transfer, unrest after conquest."""

    rule_version: str = "siege-v1"
    full_progress: int = Field(default=DEFAULT_FULL_PROGRESS, ge=1)
    troop_factor: int = Field(default=DEFAULT_TROOP_FACTOR, ge=1)
    garrison_floor: int = Field(default=DEFAULT_GARRISON_FLOOR, ge=1)
    min_step: int = Field(default=DEFAULT_MIN_STEP, ge=1)
    hold_delay: int = Field(default=DEFAULT_HOLD_DELAY, ge=1)
    conquest_unrest: Percent = DEFAULT_CONQUEST_UNREST
