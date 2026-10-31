from app.models.world_state import CounterKind, WorldState
from strategy_contracts.ids import ArmyId

ARMY_ID_PREFIX = "army_"


def next_army_id(world: WorldState) -> ArmyId:
    count = world.counters.get(CounterKind.ARMY, 0)
    candidate = f"{ARMY_ID_PREFIX}{count + 1}"
    while candidate in world.armies:
        count += 1
        candidate = f"{ARMY_ID_PREFIX}{count + 1}"
    world.counters[CounterKind.ARMY] = count + 1
    return candidate


def remove_army(world: WorldState, army_id: ArmyId) -> None:
    army = world.armies.pop(army_id)
    world.supply_failure_turns.pop(army_id, None)
    _drop_army_from_sieges(world, army_id)
    commander = world.commanders.get(army.commander_id or "")
    if commander is not None:
        commander.army_id = None


def _drop_army_from_sieges(world: WorldState, army_id: ArmyId) -> None:
    for siege in world.sieges:
        siege.army_ids = [item for item in siege.army_ids if item != army_id]
    world.sieges = [siege for siege in world.sieges if siege.army_ids]
