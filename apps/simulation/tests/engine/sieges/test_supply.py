from app.engine.logistics.supply import supply_assessment
from strategy_contracts.battle import SupplyState

from tests.engine.sieges.builders import (
    BESIEGER,
    SCENARIO,
    TARGET_REGION,
    add_siege,
    make_siege_world,
    occupy,
)


def _state(world, faction_id: str = BESIEGER) -> SupplyState:
    return supply_assessment(world, TARGET_REGION, faction_id, SCENARIO).state


def test_an_army_in_enemy_land_without_a_siege_is_isolated() -> None:
    assert _state(make_siege_world()) is SupplyState.ISOLATED


def test_the_besieger_is_not_isolated_while_the_siege_lasts() -> None:
    world = make_siege_world()
    add_siege(world)

    assert _state(world) is not SupplyState.ISOLATED


def test_the_occupier_is_not_isolated_while_it_holds_the_region() -> None:
    world = make_siege_world()
    occupy(world)

    assert _state(world) is not SupplyState.ISOLATED


def test_a_siege_by_one_faction_does_not_feed_another() -> None:
    world = make_siege_world()
    add_siege(world)

    assert _state(world, "house_dunwick") is SupplyState.ISOLATED


def test_a_siege_far_from_friendly_land_still_starves() -> None:
    world = make_siege_world()
    add_siege(world)
    world.regions["ashford"].owner_id = "house_dunwick"
    world.regions["gull_point"].owner_id = "house_dunwick"
    world.regions["aldgate"].owner_id = "house_dunwick"

    assert _state(world) is SupplyState.ISOLATED
