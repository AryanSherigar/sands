from app.engine.diplomacy.events import diplomacy_event
from app.engine.peace.truces import (
    apply_breach_consequences,
    grant_broken_promise_ground,
)
from app.engine.promises.matchers import is_breach, is_proxy_breach
from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import SwornPromiseTerm

SWORN_PROMISE_BROKEN = "sworn_promise_broken"


def _open_promises(world: WorldState) -> list[tuple[CommitmentState, SwornPromiseTerm]]:
    return [
        (commitment, commitment.term)
        for commitment in sorted(world.commitments, key=lambda item: item.id)
        if commitment.status is CommitmentStatus.ACTIVE
        and isinstance(commitment.term, SwornPromiseTerm)
    ]


def _is_party_gone(world: WorldState, term: SwornPromiseTerm) -> bool:
    return any(
        world.factions[faction_id].is_destroyed
        for faction_id in (term.promisor_id, term.beneficiary_id)
        if faction_id in world.factions
    )


def _break_promise(
    world: WorldState,
    scenario: StrategyScenario,
    commitment: CommitmentState,
    term: SwornPromiseTerm,
    phase: PhaseName,
) -> EventLogEntry:
    commitment.status = CommitmentStatus.BREACHED
    apply_breach_consequences(world, scenario, term.promisor_id)
    grant_broken_promise_ground(world, scenario, term.beneficiary_id, term.promisor_id)
    return diplomacy_event(
        SWORN_PROMISE_BROKEN,
        [term.promisor_id, term.beneficiary_id, commitment.id],
        phase=phase,
        is_major=True,
    )


def _settle_without_breach(world: WorldState, commitment: CommitmentState) -> None:
    if commitment.end_turn is not None and commitment.end_turn < world.clock.turn:
        commitment.status = CommitmentStatus.FULFILLED


def _is_breached_by_any(
    world: WorldState, term: SwornPromiseTerm, events: list[EventLogEntry]
) -> bool:
    return any(
        is_breach(term, event) or is_proxy_breach(world, term, event)
        for event in events
    )


def scan_sworn_promises(
    world: WorldState,
    scenario: StrategyScenario,
    phase_events: list[EventLogEntry],
    phase: PhaseName,
) -> list[EventLogEntry]:
    """Breach active promises matched by this phase's events; settle the rest."""
    broken: list[EventLogEntry] = []
    for commitment, term in _open_promises(world):
        if _is_party_gone(world, term):
            commitment.status = CommitmentStatus.EXPIRED
        elif _is_breached_by_any(world, term, phase_events):
            broken.append(_break_promise(world, scenario, commitment, term, phase))
        else:
            _settle_without_breach(world, commitment)
    return broken
