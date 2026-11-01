import pytest
from app.models.world_events import (
    PHASE_ORDER,
    EventCause,
    EventLogEntry,
    PhaseName,
    StateChange,
)
from pydantic import ValidationError

RFC_PHASE_NAMES = [
    "orders",
    "diplomacy",
    "movement",
    "battles",
    "sieges",
    "economy",
    "internal",
    "time",
    "events",
    "story_check",
]


def test_phase_order_matches_the_rfc() -> None:
    assert [phase.value for phase in PHASE_ORDER] == RFC_PHASE_NAMES
    assert set(PHASE_ORDER) == set(PhaseName)


def test_event_log_entry_round_trips() -> None:
    entry = EventLogEntry(
        seq=1,
        turn=2,
        phase=PhaseName.ECONOMY,
        kind="income",
        is_major=False,
        significance=1,
        cause=EventCause(
            summary_key="tax_collected", subject_ids=["ashford"], inputs={"gold": 12}
        ),
        changes=[
            StateChange(path="factions.house_ashford.treasury", before=100, after=112)
        ],
    )
    assert EventLogEntry.model_validate_json(entry.model_dump_json()) == entry


def test_float_in_a_state_change_is_rejected() -> None:
    with pytest.raises(ValidationError):
        StateChange(path="x", before=1, after=1.5)
