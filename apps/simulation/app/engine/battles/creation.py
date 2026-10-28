from collections.abc import Sequence

from app.engine.battle_records import populate_battle_contingents
from app.engine.battles.deployment import initialize_targets, reconcile_deployments
from app.engine.battles.significance import classify_battle
from app.engine.battles.supply import supply_state
from app.engine.battles.weather import weather_for
from app.engine.movement.map_index import build_map_index
from app.exceptions.base import SimulationServiceError
from app.models.world_battle import BattleState, BattleStatus
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.scenario import StrategyScenario


def _validate_members(
    world: WorldState,
    region_id: str,
    attackers: Sequence[str],
    defenders: Sequence[str],
) -> None:
    members = [*attackers, *defenders]
    if not attackers or not defenders or len(set(members)) != len(members):
        raise SimulationServiceError("battle requires distinct armies on two sides")
    locked = {
        army_id
        for battle in world.battles
        if battle.status != BattleStatus.RESOLVED
        for army_id in (*battle.attacker_army_ids, *battle.defender_army_ids)
    }
    if locked.intersection(members):
        raise SimulationServiceError("army is already engaged")
    if any(
        army_id not in world.armies or world.armies[army_id].location_id != region_id
        for army_id in members
    ):
        raise SimulationServiceError("battle armies must be present")
    _validate_sides(world, attackers, defenders)


def _validate_sides(
    world: WorldState, attackers: Sequence[str], defenders: Sequence[str]
) -> None:
    for side_ids in (attackers, defenders):
        owners = {world.armies[army_id].owner_id for army_id in side_ids}
        if any(
            relation.status == RelationStatus.WAR
            and {relation.faction_a, relation.faction_b} <= owners
            for relation in world.relations
        ):
            raise SimulationServiceError("hostile factions cannot share a battle side")
    if {world.armies[army_id].owner_id for army_id in attackers} & {
        world.armies[army_id].owner_id for army_id in defenders
    }:
        raise SimulationServiceError("faction cannot belong to both battle sides")


def _battle_identity(world: WorldState, battle_id: str | None) -> str:
    count = world.counters.get(CounterKind.BATTLE, 0) + 1
    identity = battle_id or f"battle_{count}"
    while battle_id is None and any(battle.id == identity for battle in world.battles):
        count += 1
        identity = f"battle_{count}"
    if any(battle.id == identity for battle in world.battles):
        raise SimulationServiceError("battle identity already exists")
    return identity


def create_battle(
    world: WorldState,
    region_id: str,
    attacker_ids: Sequence[str],
    defender_ids: Sequence[str],
    scenario: StrategyScenario,
    battle_id: str | None = None,
) -> BattleState:
    """Return an owned battle record without mutating world or allocating shared counters.

    The movement/campaign owner inserts it and reserves its ID. Passing battle_id
    permits that owner to allocate several contacts in one deterministic batch.
    """
    _validate_members(world, region_id, attacker_ids, defender_ids)
    battle = BattleState(
        id=_battle_identity(world, battle_id),
        region_id=region_id,
        attacker_army_ids=list(attacker_ids),
        defender_army_ids=list(defender_ids),
        created_turn=world.clock.turn,
        current_turn=world.clock.turn,
        region_controller_id=world.regions[region_id].owner_id,
        terrain=build_map_index(scenario.map).terrain[region_id],
    )
    populate_battle_contingents(world, battle)
    classify_battle(world, battle)
    _initialize_conditions(world, battle, scenario)
    initialize_targets(world, battle, scenario.tuning.battle)
    reconcile_deployments(world, battle, scenario.tuning.battle)
    return battle


def _initialize_conditions(
    world: WorldState, battle: BattleState, scenario: StrategyScenario
) -> None:
    battle.weather = weather_for(world, battle.region_id, scenario)
    battle.weather_turn = world.clock.turn
    for faction_id, contingent in sorted(battle.contingents.items()):
        contingent.supply = supply_state(world, battle.region_id, faction_id, scenario)
