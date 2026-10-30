from collections.abc import Sequence

from app.engine.commands.application import CommandAcceptance, accept_command
from app.models.battle_command import AcceptedCommand, BattleCommand, Command
from app.models.world_army import ArmyState
from app.models.world_battle import StandingPlan
from app.models.world_state import WorldState
from strategy_contracts.battle import BattleTuning, WithdrawalPolicy
from strategy_contracts.enums import RelationStatus, Terrain, TroopType
from strategy_contracts.scenario import StrategyScenario

from tests.engine.movement.builders import (
    make_army,
    make_map,
    make_scenario,
    make_world_for,
)

ATTACKER = "house_a"
DEFENDER = "house_b"
ALLY = "house_c"
REGION = "field"
BATTLE_ID = "battle_1"


def battle_fixture(
    attacker: int = 1000,
    defender: int = 1000,
    terrain: Terrain = Terrain.PLAIN,
    extra_armies: Sequence[ArmyState] = (),
    has_routes: bool = False,
    **tuning: object,
) -> tuple[WorldState, StrategyScenario]:
    terrains = {REGION: terrain, "home_a": Terrain.PLAIN, "home_b": Terrain.PLAIN}
    links = [(REGION, "home_a"), (REGION, "home_b")] if has_routes else []
    scenario = make_scenario(make_map(terrains, links))
    scenario.tuning.battle = BattleTuning(**tuning)
    armies = [
        make_army("army_a", ATTACKER, REGION, {TroopType.INFANTRY: attacker}),
        make_army("army_b", DEFENDER, REGION, {TroopType.INFANTRY: defender}),
        *extra_armies,
    ]
    world = make_world_for(
        {REGION: DEFENDER, "home_a": ATTACKER, "home_b": DEFENDER},
        armies,
        {
            (ATTACKER, DEFENDER): RelationStatus.WAR,
            (ATTACKER, ALLY): RelationStatus.ALLIANCE,
        },
    )
    return world, scenario


def start_battle(world: WorldState, scenario: StrategyScenario) -> WorldState:
    from app.engine.battles.creation import create_battle

    attackers = [army.id for army in world.armies.values() if army.owner_id != DEFENDER]
    battle = create_battle(world, REGION, attackers, ["army_b"], scenario)
    for contingent in battle.contingents.values():
        contingent.plan = StandingPlan(withdrawal_policy=WithdrawalPolicy.HOLD_AT_COST)
    world.battles.append(battle)
    return world


def command(
    payload: BattleCommand, wave: int = 1, identity: str = "cmd_1"
) -> AcceptedCommand:
    return AcceptedCommand(
        id=identity,
        operation_id=identity,
        actor_id="owner",
        faction_id=payload.faction_id,
        battle_id=BATTLE_ID,
        accepted_turn=0,
        accepted_wave=0,
        execution_turn=0,
        execution_wave=wave,
        reserved_cost=1,
        command=payload,
    )


def exchange(
    world: WorldState,
    scenario: StrategyScenario,
    commands: Sequence[AcceptedCommand] = (),
):
    from app.engine.battles.exchange import resolve_exchange

    return resolve_exchange(world, BATTLE_ID, scenario, commands, {})


def accept(
    world: WorldState,
    scenario: StrategyScenario,
    payload: Command,
    identity: str = "cmd",
    faction: str = ATTACKER,
) -> CommandAcceptance:
    return accept_command(
        world,
        scenario,
        payload,
        command_id=identity,
        operation_id=identity,
        actor_id="owner",
        faction_id=faction,
        expected_turn=world.clock.turn,
        expected_wave=world.progress.completed_waves + 1,
    )
