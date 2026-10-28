from app.models.world_diplomacy import OutrageState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scene import OutrageLevel

MOBILIZING_LEVELS = (OutrageLevel.OUTRAGED, OutrageLevel.ENRAGED)
VALUE_PER_LEVEL = 25


def outrage_of(world: WorldState, faction_id: FactionId) -> OutrageState | None:
    return next(
        (state for state in world.outrage if state.faction_id == faction_id), None
    )


def is_enraged(world: WorldState, faction_id: FactionId) -> bool:
    state = outrage_of(world, faction_id)
    return state is not None and state.level == OutrageLevel.ENRAGED


def is_mobilized(world: WorldState, faction_id: FactionId) -> bool:
    state = outrage_of(world, faction_id)
    return state is not None and world.clock.turn < state.mobilized_until_turn


def outrage_value(world: WorldState, faction_id: FactionId) -> int:
    """Level on the same 0-100 scale as Will and Strain, so it reads through the same bands."""
    state = outrage_of(world, faction_id)
    if state is None:
        return 0
    return tuple(OutrageLevel).index(state.level) * VALUE_PER_LEVEL
