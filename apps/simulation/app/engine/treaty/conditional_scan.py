from app.engine.treaty.conditional import (
    CONDITIONAL_CLAUSE_FAILED,
    CONDITIONAL_CLAUSE_TRIGGERED,
    CONDITIONAL_GATE_CLOSED,
    CONDITIONAL_GATE_OPENED,
    conditional_event,
    find_commitment,
    is_condition_met,
    open_conditionals,
)
from app.engine.treaty.registry import term_parties
from app.engine.treaty.signing import sign_inner_clause
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import ConditionalMode, ConditionalTerm

ENDED_STATUSES = (
    CommitmentStatus.FULFILLED,
    CommitmentStatus.BREACHED,
    CommitmentStatus.EXPIRED,
)


def _in_phase(events: list[EventLogEntry], phase: PhaseName) -> list[EventLogEntry]:
    return [event.model_copy(update={"phase": phase}) for event in events]


def _is_party_gone(world: WorldState, term: ConditionalTerm) -> bool:
    return any(
        world.factions[faction_id].is_destroyed
        for faction_id in term_parties(term)
        if faction_id in world.factions
    )


def _is_lapsed(world: WorldState, commitment: CommitmentState) -> bool:
    assert isinstance(commitment.term, ConditionalTerm)
    is_past_end = (
        commitment.end_turn is not None and commitment.end_turn < world.clock.turn
    )
    return is_past_end or _is_party_gone(world, commitment.term)


def _lapse(world: WorldState, commitment: CommitmentState) -> None:
    commitment.status = CommitmentStatus.EXPIRED
    inner = find_commitment(world, commitment.linked_commitment_id)
    if inner is not None and inner.status not in ENDED_STATUSES:
        inner.status = CommitmentStatus.EXPIRED


def _fire_trigger(
    world: WorldState,
    scenario: StrategyScenario,
    commitment: CommitmentState,
    phase: PhaseName,
) -> list[EventLogEntry]:
    assert isinstance(commitment.term, ConditionalTerm)
    working = world.model_copy(deep=True)
    try:
        events = sign_inner_clause(
            working, scenario, commitment.term.inner, commitment.origin_scene_id
        )
    except CampaignProgressError:
        commitment.status = CommitmentStatus.EXPIRED
        return [conditional_event(CONDITIONAL_CLAUSE_FAILED, commitment, phase)]
    fired = find_commitment(working, commitment.id)
    assert fired is not None
    fired.status = CommitmentStatus.FULFILLED
    world.__dict__.update(working.__dict__)
    triggered = conditional_event(CONDITIONAL_CLAUSE_TRIGGERED, fired, phase)
    return [*_in_phase(events, phase), triggered]


def _is_inner_over(world: WorldState, inner: CommitmentState | None) -> bool:
    if inner is None or inner.status in ENDED_STATUSES:
        return True
    return inner.end_turn is not None and inner.end_turn < world.clock.turn


def _run_gate(
    world: WorldState, commitment: CommitmentState, phase: PhaseName
) -> list[EventLogEntry]:
    assert isinstance(commitment.term, ConditionalTerm)
    inner = find_commitment(world, commitment.linked_commitment_id)
    if inner is None or _is_inner_over(world, inner):
        commitment.status = CommitmentStatus.FULFILLED
        return []
    is_met = is_condition_met(world, commitment.term)
    if is_met and inner.status is CommitmentStatus.SUSPENDED:
        inner.status = CommitmentStatus.ACTIVE
        return [conditional_event(CONDITIONAL_GATE_OPENED, commitment, phase)]
    if not is_met and inner.status is CommitmentStatus.ACTIVE:
        inner.status = CommitmentStatus.SUSPENDED
        return [conditional_event(CONDITIONAL_GATE_CLOSED, commitment, phase)]
    return []


def scan_conditional_clauses(
    world: WorldState, scenario: StrategyScenario, phase: PhaseName
) -> list[EventLogEntry]:
    """Fire due triggers and open or close gates; lapse what has expired."""
    events: list[EventLogEntry] = []
    for commitment in open_conditionals(world):
        term = commitment.term
        assert isinstance(term, ConditionalTerm)
        if _is_lapsed(world, commitment):
            _lapse(world, commitment)
        elif term.mode is ConditionalMode.GATE:
            events += _run_gate(world, commitment, phase)
        elif is_condition_met(world, term):
            events += _fire_trigger(world, scenario, commitment, phase)
    return events
