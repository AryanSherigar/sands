from app.engine.event_numbering import number_events
from app.models.world_events import EventCause, EventLogEntry, PhaseName
from app.models.world_state import CounterKind

from tests.engine.diplomacy.builders import make_world


def _events() -> list[EventLogEntry]:
    return [
        EventLogEntry(
            seq=0,
            turn=0,
            phase=PhaseName.DIPLOMACY,
            kind=kind,
            cause=EventCause(summary_key=kind),
        )
        for kind in ("first", "second")
    ]


def test_events_continue_from_the_event_counter() -> None:
    world = make_world()
    world.clock.turn = 5

    first = number_events(world, _events())
    second = number_events(world, _events())

    assert [event.seq for event in first + second] == [1, 2, 3, 4]
    assert {event.turn for event in first + second} == {5}
    assert world.counters[CounterKind.EVENT_SEQ] == 4


def test_events_stay_unnumbered_for_worlds_before_the_siege_ruleset() -> None:
    world = make_world()
    world.siege_ruleset = 0

    numbered = number_events(world, _events())

    assert [event.seq for event in numbered] == [0, 0]
    assert CounterKind.EVENT_SEQ not in world.counters
