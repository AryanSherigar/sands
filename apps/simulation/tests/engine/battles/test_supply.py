from app.models.world_region import OccupationState
from strategy_contracts.battle import SupplyState
from strategy_contracts.scenario import FactionSetup

from tests.engine.battles.builders import ATTACKER, DEFENDER, REGION, battle_fixture


def test_local_capacity_counts_all_present_armies_and_missing_capital_isolates() -> (
    None
):
    from app.engine.battles.supply import supply_state

    world, scenario = battle_fixture(100, 100, has_routes=True)
    world.regions[REGION].owner_id = ATTACKER
    world.regions[REGION].wealth = 15
    scenario.factions = [
        FactionSetup(id=ATTACKER, name="A", color="#000000", capital_region_id="home_a")
    ]
    assert supply_state(world, REGION, ATTACKER, scenario) == SupplyState.STRAINED
    world.armies["army_b"].location_id = "home_b"
    assert supply_state(world, REGION, ATTACKER, scenario) == SupplyState.SUPPLIED
    world.regions["home_a"].occupation = OccupationState(
        occupier_id=DEFENDER, siege_progress=0
    )
    assert supply_state(world, REGION, ATTACKER, scenario) == SupplyState.ISOLATED
    scenario.factions = []
    assert supply_state(world, REGION, ATTACKER, scenario) == SupplyState.ISOLATED


def test_supply_alliance_routes_reject_occupied_intermediate_regions() -> None:
    from app.engine.battles.supply import supply_state

    from tests.engine.battles.builders import ALLY

    world, scenario = battle_fixture(10, 10, has_routes=True)
    scenario.factions = [
        FactionSetup(id=ATTACKER, name="A", color="#000000", capital_region_id="home_a")
    ]
    world.regions[REGION].owner_id = ALLY
    assert supply_state(world, REGION, ATTACKER, scenario) == SupplyState.SUPPLIED
    world.regions[REGION].occupation = OccupationState(
        occupier_id=DEFENDER, siege_progress=0
    )
    assert supply_state(world, REGION, ATTACKER, scenario) == SupplyState.ISOLATED


def test_capital_absent_from_map_is_a_safe_disconnected_route() -> None:
    from app.engine.battles.supply import supply_state

    world, scenario = battle_fixture(100, 100)
    scenario.factions = [
        FactionSetup(id=ATTACKER, name="A", color="#000000", capital_region_id="home_a")
    ]
    scenario.map.regions = [
        region for region in scenario.map.regions if region.id != "home_a"
    ]
    assert supply_state(world, REGION, ATTACKER, scenario) == SupplyState.ISOLATED
