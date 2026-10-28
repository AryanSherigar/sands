from app.models.world_coalition import CoalitionState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId


def coalition_against(world: WorldState, target_id: FactionId) -> CoalitionState | None:
    return next(
        (item for item in world.coalition.coalitions if item.target_id == target_id),
        None,
    )


def is_member_against(
    world: WorldState, member_id: FactionId, target_id: FactionId
) -> bool:
    coalition = coalition_against(world, target_id)
    return coalition is not None and member_id in coalition.member_ids
