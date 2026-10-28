from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.terms import VassalTerm
from strategy_contracts.vassal import DemandKind


def vassal_term(commitment: CommitmentState) -> VassalTerm:
    assert isinstance(commitment.term, VassalTerm)
    return commitment.term


def is_vassalage_in_force(world: WorldState, commitment: CommitmentState) -> bool:
    if not isinstance(commitment.term, VassalTerm):
        return False
    if commitment.status is not CommitmentStatus.ACTIVE:
        return False
    return commitment.end_turn is None or commitment.end_turn > world.clock.turn


def active_vassalages(
    world: WorldState, faction_id: FactionId
) -> list[CommitmentState]:
    return sorted(
        (
            item
            for item in world.commitments
            if is_vassalage_in_force(world, item)
            and faction_id
            in {vassal_term(item).overlord_id, vassal_term(item).vassal_id}
        ),
        key=lambda item: item.id,
    )


def vassalage_of(world: WorldState, vassal_id: FactionId) -> CommitmentState | None:
    return next(
        (
            item
            for item in active_vassalages(world, vassal_id)
            if vassal_term(item).vassal_id == vassal_id
        ),
        None,
    )


def vassals_of(world: WorldState, overlord_id: FactionId) -> list[CommitmentState]:
    return [
        item
        for item in active_vassalages(world, overlord_id)
        if vassal_term(item).overlord_id == overlord_id
    ]


def overlord_of(world: WorldState, vassal_id: FactionId) -> FactionId | None:
    commitment = vassalage_of(world, vassal_id)
    return vassal_term(commitment).overlord_id if commitment is not None else None


def granted_share(commitment: CommitmentState, kind: DemandKind) -> int:
    term = vassal_term(commitment)
    if kind is DemandKind.TRIBUTE:
        return term.tribute_share_percent
    if kind is DemandKind.LEVY:
        return term.levy_share_percent
    return FULL_SHARE_PERCENT if term.has_garrison_rights else 0


def vassalage_by_id(world: WorldState, vassalage_id: str) -> CommitmentState | None:
    return next(
        (
            item
            for item in world.commitments
            if item.id == vassalage_id and is_vassalage_in_force(world, item)
        ),
        None,
    )


def vassalage_between(
    world: WorldState, first: FactionId, second: FactionId
) -> CommitmentState | None:
    return next(
        (
            item
            for item in active_vassalages(world, first)
            if {first, second}
            == {vassal_term(item).overlord_id, vassal_term(item).vassal_id}
        ),
        None,
    )


def vassalage_partners(world: WorldState, faction_id: FactionId) -> list[FactionId]:
    partners = {
        term.vassal_id if term.overlord_id == faction_id else term.overlord_id
        for term in (vassal_term(item) for item in active_vassalages(world, faction_id))
    }
    return sorted(partners)
