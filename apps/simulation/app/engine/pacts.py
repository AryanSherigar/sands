from uuid import UUID

from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_events import EventCause, EventLogEntry, PhaseName
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.terms import NonAggressionTerm

PACT_AGREED = "non_aggression_agreed"


def active_pacts(world: WorldState) -> list[CommitmentState]:
    return [
        commitment
        for commitment in world.commitments
        if isinstance(commitment.term, NonAggressionTerm)
        and commitment.status is CommitmentStatus.ACTIVE
        and commitment.end_turn is not None
        and commitment.end_turn > world.clock.turn
    ]


def has_active_pact(world: WorldState, faction_a: str, faction_b: str) -> bool:
    pair = {faction_a, faction_b}
    return any(
        {commitment.term.faction_a, commitment.term.faction_b} == pair
        for commitment in active_pacts(world)
    )


def _next_counter(world: WorldState, kind: CounterKind) -> int:
    count = world.counters.get(kind, 0) + 1
    world.counters[kind] = count
    return count


def _pact_event(world: WorldState, term: NonAggressionTerm) -> EventLogEntry:
    return EventLogEntry(
        seq=_next_counter(world, CounterKind.EVENT_SEQ),
        turn=world.clock.turn,
        phase=PhaseName.DIPLOMACY,
        kind=PACT_AGREED,
        is_major=True,
        cause=EventCause(
            summary_key=PACT_AGREED,
            subject_ids=[term.faction_a, term.faction_b],
            inputs={"duration_turns": term.duration_turns},
        ),
    )


def sign_pact(
    world: WorldState, term: NonAggressionTerm, origin_scene_id: UUID | None
) -> EventLogEntry:
    number = _next_counter(world, CounterKind.COMMITMENT)
    world.commitments.append(
        CommitmentState(
            id=f"commitment_{number}",
            term=term,
            start_turn=world.clock.turn,
            end_turn=world.clock.turn + term.duration_turns,
            origin_scene_id=origin_scene_id,
        )
    )
    return _pact_event(world, term)
