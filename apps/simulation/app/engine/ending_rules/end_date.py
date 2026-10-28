from app.models.world_clock import MONTHS_PER_TURN, MONTHS_PER_YEAR
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def current_year(world: WorldState) -> int:
    clock = world.clock
    elapsed_months = clock.start_month - 1 + MONTHS_PER_TURN * clock.turn
    return clock.start_year + elapsed_months // MONTHS_PER_YEAR


def is_end_date_reached(world: WorldState, scenario: StrategyScenario) -> bool:
    return current_year(world) > scenario.tuning.end_year
