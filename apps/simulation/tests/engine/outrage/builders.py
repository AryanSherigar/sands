from app.engine.outrage.ledger import raise_outrage
from app.models.world_state import WorldState
from strategy_contracts.scene import OutrageLevel

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_axes,
)

__all__ = [
    "CAUTIOUS_RIVAL",
    "PLAYER",
    "SCENARIO",
    "WRATHFUL_RIVAL",
    "enrage",
    "make_world",
    "set_axes",
]


def enrage(
    world: WorldState,
    faction_id: str = WRATHFUL_RIVAL,
    offender_id: str = PLAYER,
    level: OutrageLevel = OutrageLevel.ENRAGED,
) -> None:
    raise_outrage(
        world, SCENARIO, faction_id=faction_id, offender_id=offender_id, level=level
    )
