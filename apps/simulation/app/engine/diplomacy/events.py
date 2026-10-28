from collections.abc import Sequence

from app.models.world_events import EventCause, EventLogEntry, PhaseName, StateChange
from strategy_contracts.ids import EntityId


def diplomacy_event(
    kind: str,
    subject_ids: list[EntityId],
    inputs: dict[str, int] | None = None,
    *,
    phase: PhaseName = PhaseName.DIPLOMACY,
    is_major: bool = False,
    changes: Sequence[StateChange] = (),
) -> EventLogEntry:
    cause = EventCause(summary_key=kind, subject_ids=subject_ids, inputs=inputs or {})
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=phase,
        kind=kind,
        is_major=is_major,
        cause=cause,
        changes=list(changes),
    )
