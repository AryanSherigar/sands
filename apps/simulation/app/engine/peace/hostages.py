from app.engine.coalitions.ledger import record_atrocity
from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.reputation import shift_standing
from app.engine.peace.truces import breach_agreements
from app.models.world_events import EventLogEntry
from app.models.world_peace import HostageState
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import HostageTerm

HOSTAGE_RELEASED = "hostage_released"
HOSTAGE_HARMED = "hostage_harmed"


def find_hostage(world: WorldState, hostage_id: str) -> HostageState | None:
    return next((item for item in world.peace.hostages if item.id == hostage_id), None)


def hold_hostage(world: WorldState, term: HostageTerm, truce_id: str) -> HostageState:
    hostage = HostageState(
        id=f"hostage_{next_counter(world, CounterKind.HOSTAGE)}",
        giver_id=term.giver_id,
        holder_id=term.holder_id,
        leader_id=term.leader_id,
        release_turn=world.clock.turn + term.duration_turns,
        truce_id=truce_id,
    )
    world.peace.hostages.append(hostage)
    return hostage


def _is_lapsed(world: WorldState, hostage: HostageState) -> bool:
    giver = world.factions.get(hostage.giver_id)
    if giver is None or giver.is_destroyed or hostage.leader_id not in world.leaders:
        return True
    if world.clock.turn >= hostage.release_turn:
        return True
    is_truce_alive = any(truce.id == hostage.truce_id for truce in world.truces)
    return not is_truce_alive and not hostage.is_at_mercy


def release_due_hostages(world: WorldState) -> list[EventLogEntry]:
    released = [item for item in world.peace.hostages if _is_lapsed(world, item)]
    world.peace.hostages = [
        item for item in world.peace.hostages if item not in released
    ]
    return [
        diplomacy_event(HOSTAGE_RELEASED, [item.id, item.giver_id, item.holder_id])
        for item in released
    ]


def release_hostage(world: WorldState, hostage_id: str) -> list[EventLogEntry]:
    hostage = find_hostage(world, hostage_id)
    assert hostage is not None
    world.peace.hostages.remove(hostage)
    return [
        diplomacy_event(
            HOSTAGE_RELEASED, [hostage.id, hostage.giver_id, hostage.holder_id]
        )
    ]


def harm_hostage(
    world: WorldState,
    scenario: StrategyScenario,
    hostage_id: str,
    harmer_id: FactionId,
) -> list[EventLogEntry]:
    hostage = find_hostage(world, hostage_id)
    assert hostage is not None
    world.peace.hostages.remove(hostage)
    events = (
        []
        if hostage.is_at_mercy
        else breach_agreements(world, scenario, harmer_id, hostage.giver_id)
    )
    shift_standing(
        world.factions[harmer_id], -scenario.tuning.peace.atrocity_reputation_cost, 0
    )
    record_atrocity(world, harmer_id)
    return [
        *events,
        diplomacy_event(HOSTAGE_HARMED, [hostage.id, hostage.giver_id, harmer_id]),
    ]
