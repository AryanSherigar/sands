from app.models.world_events import EventCause, EventLogEntry, PhaseName
from app.services.turn_report_builder import build_event_lines
from tests.engine.events.builders import NPC, PLAYER, make_disaster_world


def _event(kind: str, subject: str) -> EventLogEntry:
    return EventLogEntry(
        seq=1,
        turn=0,
        phase=PhaseName.EVENTS,
        kind=kind,
        cause=EventCause(summary_key=kind, subject_ids=[subject]),
    )


def test_npc_disaster_events_never_reach_the_players_turn_report() -> None:
    world = make_disaster_world()

    lines = build_event_lines([_event("npc_event_resolved", NPC)], world, PLAYER)

    assert lines == []


def test_the_players_own_disaster_event_does_appear() -> None:
    world = make_disaster_world()

    lines = build_event_lines([_event("event_raised", PLAYER)], world, PLAYER)

    assert [line.kind for line in lines] == ["event_raised"]
