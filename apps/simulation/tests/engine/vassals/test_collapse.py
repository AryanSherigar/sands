from app.engine.vassals.collapse import free_vassals_of_collapsed_overlords
from app.engine.vassals.registry import vassalage_of, vassals_of

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    make_world,
)


def _two_vassals():
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    add_vassalage(world, PLAYER, WRATHFUL_RIVAL)
    return world


def test_collapse_frees_every_vassal_once() -> None:
    world = _two_vassals()
    world.factions[PLAYER].is_destroyed = True

    first = free_vassals_of_collapsed_overlords(world, SCENARIO)
    second = free_vassals_of_collapsed_overlords(world, SCENARIO)

    assert [event.kind for event in first] == ["vassal_freed_by_collapse"] * 2
    assert second == []
    assert vassals_of(world, PLAYER) == []
    assert world.oathbreakers == []


def test_capital_loss_frees_the_overlords_vassals() -> None:
    world = _two_vassals()
    capital = world.factions[PLAYER].capital_region_id
    world.regions[capital].owner_id = WRATHFUL_RIVAL

    free_vassals_of_collapsed_overlords(world, SCENARIO)

    assert vassalage_of(world, CAUTIOUS_RIVAL) is None


def test_healthy_overlord_keeps_its_vassals() -> None:
    world = _two_vassals()

    assert free_vassals_of_collapsed_overlords(world, SCENARIO) == []
    assert len(vassals_of(world, PLAYER)) == 2
