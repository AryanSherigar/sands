from app.engine.vassals.overreach import (
    demand_figures,
    excess_percent_of,
    raise_unrest,
)
from strategy_contracts.vassal import DemandKind

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    add_vassalage,
    make_demand,
    make_world,
    set_unrest,
)

TUNING = SCENARIO.tuning.vassal
START_UNREST = 10


def _vassal_unrest(world) -> list[int]:
    return [
        region.unrest
        for _, region in sorted(world.regions.items())
        if region.owner_id == CAUTIOUS_RIVAL
    ]


def test_covered_demand_has_no_excess() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, tribute=30)

    figures = demand_figures(commitment, DemandKind.TRIBUTE, 30, TUNING)

    assert figures.excess <= 0


def test_tribute_excess_is_asked_minus_granted_percent() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, tribute=20)

    figures = demand_figures(commitment, DemandKind.TRIBUTE, 30, TUNING)

    assert (figures.granted, figures.excess, figures.excess_percent) == (20, 10, 50)


def test_garrison_is_covered_with_rights_and_full_excess_without() -> None:
    world = make_world()
    with_rights = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, has_garrison=True)
    covered = demand_figures(with_rights, DemandKind.GARRISON, 1, TUNING)
    with_rights.term = with_rights.term.model_copy(
        update={"has_garrison_rights": False}
    )
    open_ask = demand_figures(with_rights, DemandKind.GARRISON, 1, TUNING)

    assert covered.excess <= 0
    assert open_ask.excess > 0
    assert open_ask.excess_percent == TUNING.garrison_excess_percent


def test_moderate_excess_raises_unrest_in_all_vassal_regions() -> None:
    world = make_world()
    set_unrest(world, CAUTIOUS_RIVAL, START_UNREST)
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, tribute=20)
    demand = make_demand(commitment, amount=30)

    raise_unrest(world, SCENARIO, demand)

    step = excess_percent_of(demand, TUNING) // TUNING.unrest_per_excess_divisor
    assert set(_vassal_unrest(world)) == {START_UNREST + step}


def test_huge_excess_unrest_caps_at_tuning() -> None:
    world = make_world()
    set_unrest(world, CAUTIOUS_RIVAL, START_UNREST)
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, tribute=20)

    raise_unrest(world, SCENARIO, make_demand(commitment, amount=100))

    assert set(_vassal_unrest(world)) == {START_UNREST + TUNING.unrest_cap_per_demand}


def test_unrest_never_exceeds_one_hundred() -> None:
    world = make_world()
    set_unrest(world, CAUTIOUS_RIVAL, 95)
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, tribute=20)

    raise_unrest(world, SCENARIO, make_demand(commitment, amount=100))

    assert set(_vassal_unrest(world)) == {100}


def test_levy_demand_only_touches_regions_that_supply_manpower() -> None:
    world = make_world()
    set_unrest(world, CAUTIOUS_RIVAL, START_UNREST)
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, levy=10)
    owned = sorted(
        r for r, region in world.regions.items() if region.owner_id == CAUTIOUS_RIVAL
    )
    for region_id in owned:
        world.regions[region_id].manpower = 0
    world.regions[owned[0]].manpower = 50

    raise_unrest(world, SCENARIO, make_demand(commitment, DemandKind.LEVY, 50))

    assert world.regions[owned[0]].unrest > START_UNREST
    assert all(world.regions[r].unrest == START_UNREST for r in owned[1:])
