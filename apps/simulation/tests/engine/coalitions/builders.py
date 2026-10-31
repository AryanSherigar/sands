from app.engine.coalitions.ledger import record_conquest
from app.engine.coalitions.phase import tick_coalitions
from app.engine.opinion import shift_opinion
from app.models.world_state import WorldState

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
    set_axes,
    set_war_relation,
)

__all__ = [
    "CAUTIOUS_RIVAL",
    "PLAYER",
    "SCENARIO",
    "WRATHFUL_RIVAL",
    "add_war",
    "make_coalition_world",
    "make_threat_world",
    "make_world",
    "resent",
    "set_axes",
    "set_war_relation",
]

RESENTMENT = -20
CONQUEST_COUNT = 4


def resent(world: WorldState, holder_id: str, target_id: str) -> None:
    shift_opinion(world, holder_id, target_id, "test_resentment", RESENTMENT, 0)


def make_threat_world(target_id: str = PLAYER) -> WorldState:
    world = make_world()
    owned = sorted(
        key for key, region in world.regions.items() if region.owner_id == target_id
    )
    for _ in range(CONQUEST_COUNT):
        record_conquest(world, SCENARIO, target_id, owned[0])
    for holder_id in sorted(world.factions):
        if holder_id != target_id:
            resent(world, holder_id, target_id)
    return world


ATROCITY_COUNT = 10


def make_coalition_world() -> WorldState:
    world = make_threat_world()
    world.coalition.atrocities[PLAYER] = ATROCITY_COUNT
    tick_coalitions(world, SCENARIO)
    assert world.coalition.coalitions
    return world
