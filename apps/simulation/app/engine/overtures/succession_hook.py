from app.engine.diplomacy.grounds import inherit_grounds
from app.engine.peace.succession import leader_died
from app.models.world_character import LeaderState
from app.models.world_events import EventLogEntry, StateChange
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

HEIR_SUFFIX = "_heir"
MIN_HEIR_AGE = 18
HEIR_AGE_DIVISOR = 2


def _heir_id(world: WorldState, leader_id: str) -> str:
    candidate = f"{leader_id}{HEIR_SUFFIX}"
    while candidate in world.leaders:
        candidate = f"{candidate}{HEIR_SUFFIX}"
    return candidate


def _make_heir(world: WorldState, leader: LeaderState) -> LeaderState:
    """NOTE: the heir carries the parent's traits and opinions so a dynasty keeps its character."""
    return leader.model_copy(
        update={
            "id": _heir_id(world, leader.id),
            "name": f"Heir of {leader.name}",
            "age": max(MIN_HEIR_AGE, leader.age // HEIR_AGE_DIVISOR),
            "is_alive": True,
            "stress": 0,
            "memories": [],
        },
        deep=True,
    )


def _queue_renewals(
    world: WorldState, faction_id: FactionId, leader_id: str, player_id: FactionId
) -> None:
    for lapse in world.peace.lapses:
        parties = {lapse.faction_a, lapse.faction_b}
        is_with_player = parties == {faction_id, player_id}
        is_new = lapse.truce_id not in world.overture_renewals
        if lapse.leader_id == leader_id and is_with_player and is_new:
            world.overture_renewals.append(lapse.truce_id)
    world.overture_renewals.sort()


def remove_ruler(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[EventLogEntry]:
    """Kill an NPC ruler: an heir takes over, treaties lapse, and the heir will ask the player to renew."""
    faction = world.factions[faction_id]
    leader = world.leaders.get(faction.leader_id or "")
    if faction.is_player or leader is None or not leader.is_alive:
        return []
    player_id = next(key for key, item in world.factions.items() if item.is_player)
    heir = _make_heir(world, leader)
    leader.is_alive = False
    world.leaders[heir.id] = heir
    faction.leader_id = heir.id
    inherit_grounds(world, scenario, faction_id, heir.id)
    events = leader_died(world, scenario, leader.id)
    _queue_renewals(world, faction_id, leader.id, player_id)
    return events


def remove_ruler_change(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[StateChange]:
    faction = world.factions.get(faction_id)
    if faction is None:
        return []
    before = faction.leader_id
    remove_ruler(world, scenario, faction_id)
    if faction.leader_id == before:
        return []
    path = f"factions.{faction_id}.leader_id"
    return [StateChange(path=path, before=before, after=faction.leader_id)]
