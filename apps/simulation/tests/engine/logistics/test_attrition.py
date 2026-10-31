from app.engine.campaign_completion import complete_campaign
from app.models.world_region import OccupationState
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus, TroopType
from strategy_contracts.scenario import FactionSetup, LogisticsTuning
from tests.engine.battles.builders import ATTACKER, DEFENDER, REGION, battle_fixture


def _logistics_world():
    world, scenario = battle_fixture(100, 0, has_routes=True)
    scenario.factions = [
        FactionSetup(id=ATTACKER, name="A", color="#000000", capital_region_id="home_a")
    ]
    world.logistics_ruleset = 1
    scenario.tuning.logistics = LogisticsTuning(
        strained_attrition_percent=0,
        isolated_attrition_percent=10,
        winter_attrition_percent=0,
        isolated_morale_loss=5,
        forced_withdrawal_after_isolated_turns=2,
    )
    return world, scenario


def test_campaign_attrition_is_once_per_turn_and_records_typed_loss() -> None:
    world, scenario = _logistics_world()
    world.regions["home_a"].occupation = OccupationState(
        occupier_id=DEFENDER, siege_progress=0
    )

    events = complete_campaign(world, scenario)

    army = world.armies["army_a"]
    assert army.troops[TroopType.INFANTRY] == 90
    assert army.morale == 65
    assert world.supply_failure_turns["army_a"] == 1
    attrition = [event for event in events if event.kind == "army_supply_attrition"]
    assert len(attrition) == 1
    assert attrition[0].cause.inputs == {"isolated": 10, "winter": 0}


def test_second_isolated_turn_forces_one_legal_friendly_withdrawal() -> None:
    world, scenario = _logistics_world()
    world.supply_failure_turns["army_a"] = 1
    world.regions[REGION].owner_id = DEFENDER

    events = complete_campaign(world, scenario)

    assert world.armies["army_a"].location_id == "home_a"
    assert "army_a" not in world.supply_failure_turns
    assert any(event.kind == "army_supply_withdrawal" for event in events)


def test_trapped_army_surrenders_to_enemy_present_in_its_region() -> None:
    world, scenario = _logistics_world()
    world.supply_failure_turns["army_a"] = 1
    world.regions[REGION].owner_id = DEFENDER
    for region in scenario.map.regions:
        region.neighbor_ids = []
    world.relations = [
        relation
        for relation in world.relations
        if relation.status == RelationStatus.WAR
    ]

    events = complete_campaign(world, scenario)

    assert "army_a" not in world.armies
    assert sum(prisoner.troop_count for prisoner in world.prisoners) == 90
    assert any(event.kind == "army_supply_surrender" for event in events)


def test_legacy_world_omits_the_logistics_gate_and_failure_ledger() -> None:
    world, _ = _logistics_world()
    world.logistics_ruleset = 0
    world.supply_failure_turns["army_a"] = 1
    legacy = WorldState.model_validate(world.model_dump())

    assert "logistics_ruleset" not in legacy.model_dump(mode="json")
    assert "supply_failure_turns" not in legacy.model_dump(mode="json")
