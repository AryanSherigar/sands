from app.engine.events.constants import (
    EVENT_ANSWERED_KIND,
    EVENT_FIRED_KIND,
    EVENT_NEGLECTED_KIND,
    EVENT_SUMMARY_PREFIX,
)
from app.models.world_events import (
    EventCause,
    EventLogEntry,
    PendingEvent,
    PhaseName,
    StateChange,
)


def event_fired(pending: PendingEvent) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.EVENTS,
        kind=EVENT_FIRED_KIND,
        cause=EventCause(
            summary_key=f"{EVENT_SUMMARY_PREFIX}.{pending.cause_key}",
            subject_ids=[pending.subject_id],
            inputs={**pending.cause_inputs, "tier": pending.tier},
        ),
    )


def event_answered(
    pending: PendingEvent, choice_id: str, changes: list[StateChange]
) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.EVENTS,
        kind=EVENT_ANSWERED_KIND,
        cause=EventCause(
            summary_key=f"{EVENT_SUMMARY_PREFIX}.{pending.cause_key}.{choice_id}",
            subject_ids=[pending.subject_id],
            inputs={**pending.cause_inputs, "tier": pending.tier},
        ),
        changes=changes,
    )


def event_neglected(pending: PendingEvent, changes: list[StateChange]) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.EVENTS,
        kind=EVENT_NEGLECTED_KIND,
        is_major=True,
        cause=EventCause(
            summary_key=f"{EVENT_SUMMARY_PREFIX}.{pending.cause_key}.neglected",
            subject_ids=[pending.subject_id],
            inputs={**pending.cause_inputs, "tier": pending.tier},
        ),
        changes=changes,
    )
