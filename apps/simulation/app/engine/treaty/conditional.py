from uuid import UUID

from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.treaty.registry import term_parties
from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.condition_templates import compile_clause
from strategy_contracts.terms import ConditionalTerm

CONDITIONAL_CLAUSE_SIGNED = "conditional_clause_signed"
CONDITIONAL_CLAUSE_TRIGGERED = "conditional_clause_triggered"
CONDITIONAL_CLAUSE_FAILED = "conditional_clause_failed"
CONDITIONAL_GATE_OPENED = "conditional_gate_opened"
CONDITIONAL_GATE_CLOSED = "conditional_gate_closed"
OPEN_STATUSES = (CommitmentStatus.DORMANT, CommitmentStatus.ACTIVE)


def is_condition_met(world: WorldState, term: ConditionalTerm) -> bool:
    # NOTE: engine.conditions imports negotiation, which imports treaty.signing,
    # which imports this module; importing it at module level closes the cycle.
    from app.engine.conditions import evaluate

    return evaluate(world, compile_clause(term.when))


def add_conditional_commitment(
    world: WorldState,
    term: ConditionalTerm,
    scene_id: UUID | None,
    status: CommitmentStatus,
    linked_commitment_id: str | None = None,
) -> CommitmentState:
    commitment = CommitmentState(
        id=f"commitment_{next_counter(world, CounterKind.COMMITMENT)}",
        term=term,
        start_turn=world.clock.turn,
        end_turn=world.clock.turn + term.expires_in_turns,
        status=status,
        origin_scene_id=scene_id,
        linked_commitment_id=linked_commitment_id,
    )
    world.commitments.append(commitment)
    return commitment


def open_conditionals(world: WorldState) -> list[CommitmentState]:
    return [
        commitment
        for commitment in sorted(world.commitments, key=lambda item: item.id)
        if isinstance(commitment.term, ConditionalTerm)
        and commitment.status in OPEN_STATUSES
    ]


def find_commitment(
    world: WorldState, commitment_id: str | None
) -> CommitmentState | None:
    return next((item for item in world.commitments if item.id == commitment_id), None)


def conditional_event(
    kind: str,
    commitment: CommitmentState,
    phase: PhaseName = PhaseName.DIPLOMACY,
    *,
    is_major: bool = True,
) -> EventLogEntry:
    assert isinstance(commitment.term, ConditionalTerm)
    parties = sorted(term_parties(commitment.term))
    return diplomacy_event(
        kind, [*parties, commitment.id], phase=phase, is_major=is_major
    )
