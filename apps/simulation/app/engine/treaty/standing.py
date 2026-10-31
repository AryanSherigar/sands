from app.engine.treaty.registry import term_parties
from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId


def is_at_war(world: WorldState, left: FactionId, right: FactionId) -> bool:
    low, high = sorted((left, right))
    return any(
        relation.status is RelationStatus.WAR
        for relation in world.relations
        if (relation.faction_a, relation.faction_b) == (low, high)
    )


def is_in_force(world: WorldState, commitment: CommitmentState) -> bool:
    """Active, unexpired and not overtaken by a war between its parties."""
    is_live = (
        commitment.status is CommitmentStatus.ACTIVE
        and commitment.end_turn is not None
        and commitment.end_turn > world.clock.turn
    )
    if not is_live:
        return False
    parties = sorted(term_parties(commitment.term))
    return len(parties) < 2 or not is_at_war(world, parties[0], parties[1])
