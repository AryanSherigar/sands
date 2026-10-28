from app.models.world_events import EventCause, EventLogEntry, PhaseName
from app.models.world_state import CounterKind, WorldState


def stamp_ai_event(world: WorldState, kind: str, cause: EventCause) -> EventLogEntry:
    sequence = world.counters.get(CounterKind.EVENT_SEQ, 0) + 1
    world.counters[CounterKind.EVENT_SEQ] = sequence
    return EventLogEntry(
        seq=sequence,
        turn=world.clock.turn,
        phase=PhaseName.ORDERS,
        kind=kind,
        cause=cause,
    )
