from app.models.world_diplomacy import WarState
from app.models.world_state import WorldState

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

__all__ = [
    "CAUTIOUS_RIVAL",
    "PLAYER",
    "SCENARIO",
    "WRATHFUL_RIVAL",
    "add_war",
    "make_world",
]


def add_war(
    world: WorldState,
    attacker_id: str = WRATHFUL_RIVAL,
    defender_id: str = PLAYER,
    war_id: str = "war_1",
) -> WarState:
    war = WarState(
        id=war_id,
        attacker_id=attacker_id,
        defender_id=defender_id,
        participant_ids=[attacker_id, defender_id],
        started_turn=world.clock.turn,
    )
    world.wars.append(war)
    return war
