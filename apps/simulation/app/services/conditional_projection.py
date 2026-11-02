from app.models.api_world_view import ConditionalClauseView
from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.terms import ConditionalMode, ConditionalTerm, term_party_ids

LIVE_STATUSES = (CommitmentStatus.DORMANT, CommitmentStatus.ACTIVE)


def _gate_state(world: WorldState, commitment: CommitmentState) -> str:
    inner = next(
        (
            item
            for item in world.commitments
            if item.id == commitment.linked_commitment_id
        ),
        None,
    )
    is_open = inner is not None and inner.status is CommitmentStatus.ACTIVE
    return "gate_open" if is_open else "gate_closed"


def _state_of(
    world: WorldState, commitment: CommitmentState, term: ConditionalTerm
) -> str:
    if term.mode is ConditionalMode.TRIGGER:
        return "pending"
    return _gate_state(world, commitment)


def project_conditional_clauses(
    world: WorldState, faction_id: FactionId
) -> list[ConditionalClauseView]:
    return [
        ConditionalClauseView(
            commitment_id=commitment.id,
            mode=commitment.term.mode.value,
            template=commitment.term.when.template,
            condition_faction_id=commitment.term.when.faction_id,
            condition_value=commitment.term.when.value,
            condition_region_id=commitment.term.when.region_id,
            inner_kind=commitment.term.inner.kind,
            party_ids=sorted(term_party_ids(commitment.term.inner)),
            state=_state_of(world, commitment, commitment.term),
            end_turn=commitment.end_turn,
        )
        for commitment in sorted(world.commitments, key=lambda item: item.id)
        if commitment.status in LIVE_STATUSES
        and isinstance(commitment.term, ConditionalTerm)
        and faction_id in term_party_ids(commitment.term.inner)
    ]
