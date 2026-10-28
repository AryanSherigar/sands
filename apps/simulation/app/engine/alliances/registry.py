from app.models.world_diplomacy import CommitmentState, CommitmentStatus, RelationState
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId
from strategy_contracts.terms import AllianceTerm


def alliance_term(commitment: CommitmentState) -> AllianceTerm:
    assert isinstance(commitment.term, AllianceTerm)
    return commitment.term


def _is_in_force(world: WorldState, commitment: CommitmentState) -> bool:
    if not isinstance(commitment.term, AllianceTerm):
        return False
    if commitment.status is not CommitmentStatus.ACTIVE:
        return False
    return commitment.end_turn is None or commitment.end_turn > world.clock.turn


def active_alliances(world: WorldState, faction_id: FactionId) -> list[CommitmentState]:
    return sorted(
        (
            item
            for item in world.commitments
            if _is_in_force(world, item)
            and faction_id
            in {alliance_term(item).faction_a, alliance_term(item).faction_b}
        ),
        key=lambda item: item.id,
    )


def alliance_between(
    world: WorldState, faction_a: FactionId, faction_b: FactionId
) -> CommitmentState | None:
    return next(
        (
            item
            for item in active_alliances(world, faction_a)
            if faction_b
            in {alliance_term(item).faction_a, alliance_term(item).faction_b}
        ),
        None,
    )


def allies_of(world: WorldState, faction_id: FactionId) -> list[FactionId]:
    partners: set[FactionId] = set()
    for item in active_alliances(world, faction_id):
        term = alliance_term(item)
        partners.add(term.faction_b if term.faction_a == faction_id else term.faction_a)
    return sorted(partners)


def restore_peace_after_alliance(
    world: WorldState, faction_a: FactionId, faction_b: FactionId
) -> None:
    pair = tuple(sorted((faction_a, faction_b)))
    for relation in world.relations:
        is_pair = (relation.faction_a, relation.faction_b) == pair
        if is_pair and relation.status == RelationStatus.ALLIANCE:
            relation.status = RelationStatus.PEACE
            relation.since_turn = world.clock.turn


def set_pair_relation(
    world: WorldState,
    faction_a: FactionId,
    faction_b: FactionId,
    status: RelationStatus,
) -> None:
    low, high = sorted((faction_a, faction_b))
    for relation in world.relations:
        if (relation.faction_a, relation.faction_b) == (low, high):
            relation.status = status
            relation.since_turn = world.clock.turn
            return
    world.relations.append(
        RelationState(
            faction_a=low,
            faction_b=high,
            status=status,
            since_turn=world.clock.turn,
        )
    )
