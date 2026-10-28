from app.engine.battle_records import populate_battle_contingents
from app.models.world_battle import BattleState, BattleStatus
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.ids import ArmyId, RegionId

BATTLE_ID_PREFIX = "battle_"
STATUS_RESOLVED = BattleStatus.RESOLVED
STATUS_AWAITING_COMMANDS = BattleStatus.AWAITING_COMMANDS


def armies_in_open_battle(world: WorldState) -> set[ArmyId]:
    return {
        army_id
        for battle in world.pending_battles
        if battle.status != STATUS_RESOLVED
        for army_id in (*battle.attacker_army_ids, *battle.defender_army_ids)
    }


def _find_open_battle(world: WorldState, region_id: RegionId) -> BattleState | None:
    for battle in world.pending_battles:
        if battle.region_id == region_id and battle.status != STATUS_RESOLVED:
            return battle
    return None


def _new_battle(world: WorldState, region_id: RegionId) -> BattleState:
    count = world.counters.get(CounterKind.BATTLE, 0) + 1
    world.counters[CounterKind.BATTLE] = count
    battle = BattleState(
        id=f"{BATTLE_ID_PREFIX}{count}",
        region_id=region_id,
        attacker_army_ids=[],
        defender_army_ids=[],
        # NOTE: the battles phase decides whether a battle is big enough to take command of.
        is_big=False,
        status=STATUS_AWAITING_COMMANDS,
        created_turn=world.clock.turn,
        current_turn=world.clock.turn,
        region_controller_id=world.regions[region_id].owner_id,
    )
    world.pending_battles.append(battle)
    return battle


def _stop_marching(world: WorldState, army_ids: list[ArmyId]) -> None:
    for army_id in army_ids:
        world.armies[army_id].march = None
        world.armies[army_id].order = None


def open_or_join_battle(
    world: WorldState,
    region_id: RegionId,
    attacker_ids: list[ArmyId],
    defender_ids: list[ArmyId],
) -> BattleState:
    battle = _find_open_battle(world, region_id) or _new_battle(world, region_id)
    defenders = set(battle.defender_army_ids)
    attackers = set(battle.attacker_army_ids) | (set(attacker_ids) - defenders)
    defenders |= set(defender_ids) - attackers
    battle.attacker_army_ids = sorted(attackers)
    battle.defender_army_ids = sorted(defenders)
    populate_battle_contingents(world, battle)
    _stop_marching(world, [*attacker_ids, *defender_ids])
    return battle
