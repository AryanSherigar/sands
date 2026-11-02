from app.models.api_world_view import SwornPromiseHistoryView, SwornPromiseView
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.terms import SwornPromiseTerm


def project_sworn_promises(
    world: WorldState, faction_id: FactionId
) -> list[SwornPromiseView]:
    return [
        SwornPromiseView(
            commitment_id=commitment.id,
            promisor_id=commitment.term.promisor_id,
            beneficiary_id=commitment.term.beneficiary_id,
            promise=commitment.term.promise,
            subject_id=commitment.term.subject_id,
            end_turn=commitment.end_turn,
        )
        for commitment in world.commitments
        if commitment.status is CommitmentStatus.ACTIVE
        and isinstance(commitment.term, SwornPromiseTerm)
        and faction_id in (commitment.term.promisor_id, commitment.term.beneficiary_id)
    ]


RESOLVED_OUTCOMES = {
    CommitmentStatus.BREACHED: "breached",
    CommitmentStatus.FULFILLED: "fulfilled",
    CommitmentStatus.EXPIRED: "expired",
}
HISTORY_LIMIT = 10


def project_sworn_promise_history(
    world: WorldState, faction_id: FactionId
) -> list[SwornPromiseHistoryView]:
    resolved = [
        SwornPromiseHistoryView(
            commitment_id=commitment.id,
            promisor_id=commitment.term.promisor_id,
            beneficiary_id=commitment.term.beneficiary_id,
            promise=commitment.term.promise,
            subject_id=commitment.term.subject_id,
            outcome=RESOLVED_OUTCOMES[commitment.status],
            end_turn=commitment.end_turn,
        )
        for commitment in world.commitments
        if commitment.status in RESOLVED_OUTCOMES
        and isinstance(commitment.term, SwornPromiseTerm)
        and faction_id in (commitment.term.promisor_id, commitment.term.beneficiary_id)
    ]
    return resolved[-HISTORY_LIMIT:]
