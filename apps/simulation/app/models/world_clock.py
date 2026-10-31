from app.models.base import WorldModel
from pydantic import Field

MONTHS_PER_TURN = 2
TURNS_PER_YEAR = 6
MONTHS_PER_YEAR = 12


class TurnClock(WorldModel):
    turn: int = Field(ge=0)
    start_year: int
    start_month: int = Field(ge=1, le=12)


def current_month(clock: TurnClock) -> int:
    elapsed_months = clock.start_month - 1 + MONTHS_PER_TURN * clock.turn
    return elapsed_months % MONTHS_PER_YEAR + 1


class RngState(WorldModel):
    seed: int
