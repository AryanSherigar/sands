from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState


def number_events(
    world: WorldState, events: list[EventLogEntry]
) -> list[EventLogEntry]:
    # NOTE: worlds from before siege_ruleset 1 keep their events unnumbered, because
    # numbering moves the event counter and would change their recorded replay hashes.
    if world.siege_ruleset < 1:
        return events
    last_sequence = world.counters.get(CounterKind.EVENT_SEQ, 0)
    numbered = [
        event.model_copy(
            update={"seq": last_sequence + offset, "turn": world.clock.turn}
        )
        for offset, event in enumerate(events, start=1)
    ]
    world.counters[CounterKind.EVENT_SEQ] = last_sequence + len(numbered)
    return numbered
