from app.models.world_clock import MONTHS_PER_TURN, MONTHS_PER_YEAR, TurnClock
from app.models.world_state import WorldState


def _year_at(clock: TurnClock, turn: int) -> int:
    elapsed_months = clock.start_month - 1 + MONTHS_PER_TURN * turn
    return clock.start_year + elapsed_months // MONTHS_PER_YEAR


def is_new_year(world: WorldState) -> bool:
    turn = world.clock.turn
    if turn < 1:
        return False
    return _year_at(world.clock, turn) > _year_at(world.clock, turn - 1)


def age_leaders(world: WorldState) -> None:
    if not is_new_year(world):
        return
    for leader_id in sorted(world.leaders):
        leader = world.leaders[leader_id]
        if leader.is_alive:
            leader.age += 1
