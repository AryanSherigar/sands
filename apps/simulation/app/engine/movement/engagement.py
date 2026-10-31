from app.engine.battle_records import populate_battle_contingents
from app.models.world_battle import BattleSide, BattleState, BattleStatus
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


def _settled_side(
    world: WorldState, battle: BattleState, army_id: ArmyId, labelled: BattleSide
) -> BattleSide:
    contingent = battle.contingents.get(world.armies[army_id].owner_id)
    return labelled if contingent is None else contingent.side


def _split_by_settled_side(
    world: WorldState,
    battle: BattleState,
    attacker_ids: list[ArmyId],
    defender_ids: list[ArmyId],
) -> tuple[set[ArmyId], set[ArmyId]]:
    sides: dict[BattleSide, set[ArmyId]] = {
        BattleSide.ATTACKER: set(),
        BattleSide.DEFENDER: set(),
    }
    labelled = (
        (attacker_ids, BattleSide.ATTACKER),
        (defender_ids, BattleSide.DEFENDER),
    )
    for army_ids, side in labelled:
        for army_id in army_ids:
            sides[_settled_side(world, battle, army_id, side)].add(army_id)
    return sides[BattleSide.ATTACKER], sides[BattleSide.DEFENDER]


def open_or_join_battle(
    world: WorldState,
    region_id: RegionId,
    attacker_ids: list[ArmyId],
    defender_ids: list[ArmyId],
) -> BattleState:
    battle = _find_open_battle(world, region_id) or _new_battle(world, region_id)
    joining_attackers, joining_defenders = _split_by_settled_side(
        world, battle, attacker_ids, defender_ids
    )
    defenders = set(battle.defender_army_ids)
    attackers = set(battle.attacker_army_ids) | (joining_attackers - defenders)
    defenders |= joining_defenders - attackers
    battle.attacker_army_ids = sorted(attackers)
    battle.defender_army_ids = sorted(defenders)
    populate_battle_contingents(world, battle)
    _stop_marching(world, [*attacker_ids, *defender_ids])
    return battle
