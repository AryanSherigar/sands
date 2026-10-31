from app.engine.sieges.advance import advance_sieges
from app.models.world_diplomacy import RelationStatus

from tests.engine.sieges.builders import (
    BESIEGER,
    BESIEGER_ARMY,
    SCENARIO,
    TARGET_REGION,
    add_siege,
    make_siege_world,
)


def test_progress_accumulates_each_turn() -> None:
    world = make_siege_world()
    add_siege(world)

    first = advance_sieges(world, SCENARIO)
    second = advance_sieges(world, SCENARIO)

    assert world.sieges[0].progress == 50
    assert [event.kind for event in first + second] == ["siege_progressed"] * 2


def test_second_army_adds_its_troops_to_progress() -> None:
    world = make_siege_world()
    world.armies["army_ashford_2"].location_id = TARGET_REGION
    add_siege(world)

    advance_sieges(world, SCENARIO)

    assert world.sieges[0].progress == 38
    assert world.sieges[0].army_ids == ["army_ashford_1", "army_ashford_2"]


def test_full_progress_sets_occupation_and_ends_the_siege() -> None:
    world = make_siege_world()
    add_siege(world, progress=80)

    events = advance_sieges(world, SCENARIO)

    occupation = world.regions[TARGET_REGION].occupation
    assert occupation is not None
    assert (occupation.occupier_id, occupation.siege_progress) == (BESIEGER, 100)
    assert occupation.hold_turns == 0
    assert world.sieges == []
    assert [event.kind for event in events] == ["region_occupied"]


def test_siege_dropped_when_the_army_leaves() -> None:
    world = make_siege_world()
    add_siege(world)
    world.armies[BESIEGER_ARMY].location_id = "ashford"

    events = advance_sieges(world, SCENARIO)

    assert world.sieges == []
    assert events == []


def test_siege_dropped_when_the_war_ends() -> None:
    world = make_siege_world()
    add_siege(world)
    for relation in world.relations:
        relation.status = RelationStatus.PEACE

    advance_sieges(world, SCENARIO)

    assert world.sieges == []
    assert world.regions[TARGET_REGION].occupation is None
