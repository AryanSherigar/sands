from app.engine.pressure.strain import compute_strain
from app.models.world_faction import LoanState
from hypothesis import given
from hypothesis import strategies as st

from tests.engine.pressure.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)


def _owned(world, faction_id):
    return [r for r in world.regions.values() if r.owner_id == faction_id]


def test_peace_faction_has_zero_strain() -> None:
    reading = compute_strain(make_world(), SCENARIO, PLAYER)

    assert reading.value == 0
    assert reading.factors == {}


def test_debt_raises_strain_more_than_equal_treasury_loss() -> None:
    indebted = make_world()
    add_war(indebted)
    indebted.factions[PLAYER].loans = [
        LoanState(principal=50, interest_percent=10, turns_remaining=5)
    ]
    poorer = make_world()
    add_war(poorer)
    poorer.factions[PLAYER].treasury -= 50

    assert (
        compute_strain(indebted, SCENARIO, PLAYER).value
        > compute_strain(poorer, SCENARIO, PLAYER).value
    )


def test_empty_treasury_adds_strain() -> None:
    world = make_world()
    add_war(world)
    baseline = compute_strain(world, SCENARIO, PLAYER).value
    world.factions[PLAYER].treasury = 0

    assert compute_strain(world, SCENARIO, PLAYER).value > baseline


def test_manpower_depletion_raises_strain() -> None:
    world = make_world()
    add_war(world)
    baseline = compute_strain(world, SCENARIO, PLAYER).factors.get("manpower", 0)
    for region in _owned(world, PLAYER):
        region.manpower = 0

    assert compute_strain(world, SCENARIO, PLAYER).factors["manpower"] > baseline


def test_devastation_raises_strain_proportionally() -> None:
    world = make_world()
    add_war(world)
    region = _owned(world, PLAYER)[0]
    world.pressure.devastation[region.id] = 40
    low = compute_strain(world, SCENARIO, PLAYER).factors["devastation"]
    world.pressure.devastation[region.id] = 80

    assert compute_strain(world, SCENARIO, PLAYER).factors["devastation"] == 2 * low


def test_home_unrest_raises_strain() -> None:
    world = make_world()
    add_war(world)
    baseline = compute_strain(world, SCENARIO, PLAYER).factors["unrest"]
    for region in _owned(world, PLAYER):
        region.unrest = 90

    assert compute_strain(world, SCENARIO, PLAYER).factors["unrest"] > baseline


def test_supply_failures_raise_strain() -> None:
    world = make_world()
    add_war(world)
    army = next(a for a in world.armies.values() if a.owner_id == PLAYER)
    world.supply_failure_turns[army.id] = 2

    assert compute_strain(world, SCENARIO, PLAYER).factors["supply"] > 0


def test_second_front_adds_fixed_amount_per_extra_war() -> None:
    world = make_world()
    add_war(world)
    add_war(world, attacker_id="house_carrow", war_id="war_2")

    reading = compute_strain(world, SCENARIO, PLAYER)

    assert (
        reading.factors["second_front"] == SCENARIO.tuning.pressure.second_front_strain
    )


def test_stalemate_strain_grows_with_idle_turns() -> None:
    world = make_world()
    war = add_war(world)
    world.pressure.stalemate_turns[war.id] = 2
    short = compute_strain(world, SCENARIO, PLAYER).factors["stalemate"]
    world.pressure.stalemate_turns[war.id] = 8

    assert compute_strain(world, SCENARIO, PLAYER).factors["stalemate"] > short


def test_strain_is_clamped_to_0_100() -> None:
    world = make_world()
    add_war(world)
    for region in _owned(world, PLAYER):
        region.manpower, region.unrest = 0, 100
        world.pressure.devastation[region.id] = 100
    world.factions[PLAYER].treasury = 0
    world.factions[PLAYER].loans = [
        LoanState(principal=10_000, interest_percent=10, turns_remaining=5)
    ]
    world.pressure.stalemate_turns["war_1"] = 500

    assert compute_strain(world, SCENARIO, PLAYER).value == 100


def test_destroyed_faction_reads_zero() -> None:
    world = make_world()
    add_war(world, attacker_id=WRATHFUL_RIVAL)
    world.factions[PLAYER].is_destroyed = True

    assert compute_strain(world, SCENARIO, PLAYER).value == 0


@given(st.integers(0, 100), st.integers(0, 100))
def test_strain_monotonic_in_devastation(first: int, second: int) -> None:
    world = make_world()
    add_war(world)
    region = _owned(world, PLAYER)[0]
    low, high = sorted((first, second))
    world.pressure.devastation[region.id] = low
    low_value = compute_strain(world, SCENARIO, PLAYER).value
    world.pressure.devastation[region.id] = high

    assert compute_strain(world, SCENARIO, PLAYER).value >= low_value
