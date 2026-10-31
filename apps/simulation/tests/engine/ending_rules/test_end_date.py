from app.engine.ending_rules.end_date import is_end_date_reached

from tests.engine.ending_rules.builders import SCENARIO, make_world

MONTHS_PER_YEAR = 12


def _world_at_year(year_offset: int, extra_months: int = 0):
    world = make_world()
    world.clock.start_month = 1
    world.clock.start_year = SCENARIO.tuning.end_year - year_offset
    world.clock.turn = 0
    world.clock.start_month = 1 + extra_months
    return world


def test_end_date_not_reached_in_final_year() -> None:
    assert not is_end_date_reached(_world_at_year(0), SCENARIO)


def test_end_date_reached_after_end_year() -> None:
    assert is_end_date_reached(_world_at_year(-1), SCENARIO)


def test_end_date_advances_with_turns() -> None:
    world = _world_at_year(0)
    assert not is_end_date_reached(world, SCENARIO)
    world.clock.turn = MONTHS_PER_YEAR
    assert is_end_date_reached(world, SCENARIO)
