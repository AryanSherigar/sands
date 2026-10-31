import pytest
from app.engine.campaign import begin_campaign
from app.engine.commands.cancellation import cancel_command
from app.engine.hashing import world_hash
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import CommandStatus
from app.models.orders import AttackOrder, MoveArmyOrder
from app.models.world_battle import BattleStatus
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario

from tests.engine.battles.builders import ATTACKER, battle_fixture
from tests.engine.battles.test_order_planning import plan

ENEMY_REGION = "field"
HOME_REGION = "home_a"


def attack_world() -> tuple[WorldState, StrategyScenario]:
    world, scenario = battle_fixture(has_routes=True)
    for faction in world.factions.values():
        faction.is_player = faction.id == ATTACKER
    world.armies["army_a"].location_id = HOME_REGION
    return world, scenario


def attack(region_id: str = ENEMY_REGION, army_id: str = "army_a") -> AttackOrder:
    return AttackOrder(faction_id=ATTACKER, army_id=army_id, target_region_id=region_id)


def test_attack_on_an_enemy_region_is_queued_and_costs_points() -> None:
    world, scenario = attack_world()
    points = world.factions[ATTACKER].orders_remaining
    accepted = plan(world, scenario, attack(), "attack")
    assert accepted.world.factions[ATTACKER].orders_remaining == points - 1
    assert accepted.world.accepted_commands[0].status == CommandStatus.ACCEPTED


def test_attack_on_a_region_that_is_not_hostile_is_refused_for_free() -> None:
    world, scenario = attack_world()
    before = world_hash(world)
    with pytest.raises(CommandError) as raised:
        plan(world, scenario, attack(HOME_REGION), "attack")
    assert (raised.value.code, raised.value.status_code) == ("target_not_hostile", 422)
    assert world_hash(world) == before


def test_attack_with_another_factions_army_is_not_found() -> None:
    world, scenario = attack_world()
    with pytest.raises(CommandError) as raised:
        plan(world, scenario, attack(army_id="army_b"), "attack")
    assert raised.value.status_code == 404


def test_an_army_has_one_movement_slot_shared_by_move_and_attack() -> None:
    world, scenario = attack_world()
    queued = plan(world, scenario, attack(), "attack").world
    move = MoveArmyOrder(faction_id=ATTACKER, army_id="army_a", to_region_id="home_b")
    with pytest.raises(CommandError) as raised:
        plan(queued, scenario, move, "move")
    assert raised.value.code == "duplicate_slot"


def test_attack_can_be_removed_before_end_turn() -> None:
    world, scenario = attack_world()
    points = world.factions[ATTACKER].orders_remaining
    queued = plan(world, scenario, attack(), "attack").world
    removed = cancel_command(
        queued, scenario, "attack", faction_id=ATTACKER, expected_turn=0
    )
    assert removed.accepted_commands == []
    assert removed.factions[ATTACKER].orders_remaining == points


def test_queued_attack_marches_then_opens_a_battle_awaiting_commands() -> None:
    world, scenario = attack_world()
    queued = plan(world, scenario, attack(), "attack").world
    marching = begin_campaign(queued, scenario).world
    assert marching.accepted_commands[0].status == CommandStatus.APPLIED
    assert marching.armies["army_a"].order.target_id == ENEMY_REGION
    assert marching.battles == []
    fighting = begin_campaign(marching, scenario).world
    [battle] = fighting.battles
    assert battle.region_id == ENEMY_REGION
    assert battle.attacker_army_ids == ["army_a"]
    assert battle.status == BattleStatus.AWAITING_COMMANDS
