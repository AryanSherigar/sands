from app.engine.alliances.registry import (
    active_alliances,
    alliance_between,
    alliance_term,
    allies_of,
)
from app.models.world_diplomacy import CommitmentStatus

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    WRATHFUL_RIVAL,
    add_alliance,
    make_world,
)


def test_allies_of_lists_partners_sorted() -> None:
    world = make_world()
    add_alliance(world, PLAYER, WRATHFUL_RIVAL)
    add_alliance(world, CAUTIOUS_RIVAL, PLAYER)

    assert allies_of(world, PLAYER) == [CAUTIOUS_RIVAL, WRATHFUL_RIVAL]


def test_allies_of_ignores_expired_and_breached() -> None:
    world = make_world()
    breached = add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    breached.status = CommitmentStatus.BREACHED
    add_alliance(world, PLAYER, WRATHFUL_RIVAL, duration_turns=3)
    world.clock.turn += 3

    assert allies_of(world, PLAYER) == []


def test_alliance_between_is_symmetric() -> None:
    world = make_world()
    commitment = add_alliance(world, PLAYER, CAUTIOUS_RIVAL)

    assert alliance_between(world, CAUTIOUS_RIVAL, PLAYER) == commitment
    assert alliance_between(world, PLAYER, WRATHFUL_RIVAL) is None


def test_active_alliances_sorted_by_id() -> None:
    world = make_world()
    add_alliance(world, PLAYER, WRATHFUL_RIVAL)
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)

    ids = [item.id for item in active_alliances(world, PLAYER)]

    assert ids == sorted(ids)


def test_alliance_term_returns_the_stored_term() -> None:
    world = make_world()
    commitment = add_alliance(world, PLAYER, CAUTIOUS_RIVAL)

    assert alliance_term(commitment).faction_a == PLAYER
