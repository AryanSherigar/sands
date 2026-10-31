from app.models.api_world_view import SwornPromiseView
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
