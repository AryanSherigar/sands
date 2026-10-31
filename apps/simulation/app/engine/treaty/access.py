from app.engine.treaty.standing import is_in_force
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.terms import MilitaryAccessTerm


def has_military_access(
    world: WorldState, grantee_id: FactionId, grantor_id: FactionId
) -> bool:
    if world.treaty_ruleset < 1:
        return False
    return any(
        isinstance(item.term, MilitaryAccessTerm)
        and (item.term.grantee_id, item.term.grantor_id) == (grantee_id, grantor_id)
        and is_in_force(world, item)
        for item in world.commitments
    )
