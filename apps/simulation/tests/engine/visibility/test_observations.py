from app.engine.visibility.observations import record_visible_observations
from app.models.world_state import CURRENT_VISIBILITY_RULESET
from strategy_contracts.enums import Terrain
from tests.engine.movement.builders import (
    FACTION_A,
    make_map,
    make_scenario,
    make_world_for,
)


def test_visible_regions_create_staleable_observations() -> None:
    scenario = make_scenario(
        make_map({"home": Terrain.PLAIN, "border": Terrain.PLAIN}, [("home", "border")])
    )
    world = make_world_for({"home": FACTION_A, "border": "house_b"}, turn=4)
    world.visibility_ruleset = CURRENT_VISIBILITY_RULESET

    record_visible_observations(world, scenario)

    intel = world.factions[FACTION_A].intel["border"]
    assert intel.owner_id == "house_b"
    assert intel.last_seen_turn == 4
    assert intel.garrison_low <= intel.garrison_high


def test_lost_sight_does_not_refresh_an_observation() -> None:
    scenario = make_scenario(
        make_map({"home": Terrain.PLAIN, "border": Terrain.PLAIN}, [("home", "border")])
    )
    world = make_world_for({"home": FACTION_A, "border": "house_b"}, turn=4)
    world.visibility_ruleset = CURRENT_VISIBILITY_RULESET
    record_visible_observations(world, scenario)
    world.regions["home"].owner_id = "house_b"
    world.regions["border"].owner_id = "house_c"
    world.clock.turn = 5

    record_visible_observations(world, scenario)

    intel = world.factions[FACTION_A].intel["border"]
    assert intel.owner_id == "house_b"
    assert intel.last_seen_turn == 4
