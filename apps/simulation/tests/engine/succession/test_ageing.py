from app.engine.succession.ageing import age_leaders, is_new_year
from app.models.world_state import WorldState

from tests.engine.succession.builders import PLAYER, leader_of, make_succession_world


def _world_at(turn: int, start_month: int) -> WorldState:
    world = make_succession_world()
    world.clock.turn = turn
    world.clock.start_month = start_month
    return world


def test_age_increments_only_on_year_boundary() -> None:
    assert not is_new_year(_world_at(turn=1, start_month=1))
    assert is_new_year(_world_at(turn=1, start_month=12))
    assert not is_new_year(_world_at(turn=0, start_month=12))
    assert is_new_year(_world_at(turn=6, start_month=1))


def test_age_leaders_adds_one_year_to_living_leaders_on_the_boundary() -> None:
    world = _world_at(turn=1, start_month=12)
    leader = leader_of(world, PLAYER)
    before = leader.age

    age_leaders(world)

    assert leader.age == before + 1


def test_no_aging_off_the_boundary() -> None:
    world = _world_at(turn=1, start_month=1)
    leader = leader_of(world, PLAYER)
    before = leader.age

    age_leaders(world)

    assert leader.age == before


def test_dead_leaders_do_not_age() -> None:
    world = _world_at(turn=1, start_month=12)
    leader = leader_of(world, PLAYER)
    leader.is_alive = False
    before = leader.age

    age_leaders(world)

    assert leader.age == before
