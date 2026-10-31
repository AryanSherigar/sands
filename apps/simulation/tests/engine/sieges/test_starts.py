from app.engine.sieges.starts import start_sieges
from app.models.world_diplomacy import RelationStatus
from app.models.world_region import OccupationState
from app.models.world_siege import SiegeState

from tests.engine.sieges.builders import (
    BESIEGER,
    BESIEGER_ARMY,
    SCENARIO,
    TARGET_OWNER,
    TARGET_REGION,
    add_resolved_battle,
    make_siege_world,
)


def test_battle_win_starts_siege() -> None:
    world = make_siege_world()
    add_resolved_battle(world)

    events = start_sieges(world, SCENARIO)

    assert world.sieges == [
        SiegeState(
            region_id=TARGET_REGION,
            besieger_id=BESIEGER,
            army_ids=[BESIEGER_ARMY],
            progress=0,
        )
    ]
    assert [event.kind for event in events] == ["siege_started"]
    assert events[0].cause.subject_ids == [BESIEGER, TARGET_REGION, BESIEGER_ARMY]


def test_no_siege_when_not_at_war() -> None:
    world = make_siege_world()
    for relation in world.relations:
        relation.status = RelationStatus.PEACE
    add_resolved_battle(world)

    assert start_sieges(world, SCENARIO) == []
    assert world.sieges == []


def test_no_siege_on_already_occupied_region() -> None:
    world = make_siege_world()
    world.regions[TARGET_REGION].occupation = OccupationState(
        occupier_id=BESIEGER, siege_progress=100
    )
    add_resolved_battle(world)

    assert start_sieges(world, SCENARIO) == []


def test_no_siege_from_a_battle_of_an_earlier_turn() -> None:
    world = make_siege_world()
    battle = add_resolved_battle(world)
    battle.current_turn = world.clock.turn + 1

    assert start_sieges(world, SCENARIO) == []


def test_no_siege_when_the_winner_does_not_hold_the_region() -> None:
    world = make_siege_world()
    world.armies[BESIEGER_ARMY].location_id = "ashford"
    add_resolved_battle(world)

    assert start_sieges(world, SCENARIO) == []


def test_no_siege_when_the_owner_still_has_an_army_there() -> None:
    world = make_siege_world()
    world.armies["army_carrow_1"] = world.armies["army_carrow_2"].model_copy(
        update={"id": "army_carrow_1", "location_id": TARGET_REGION}
    )
    add_resolved_battle(world)

    assert start_sieges(world, SCENARIO) == []


def test_no_siege_on_the_winners_own_region() -> None:
    world = make_siege_world()
    world.regions[TARGET_REGION].owner_id = BESIEGER
    add_resolved_battle(world)

    assert start_sieges(world, SCENARIO) == []


def test_two_same_faction_armies_make_one_siege() -> None:
    world = make_siege_world()
    world.armies["army_ashford_2"].location_id = TARGET_REGION
    add_resolved_battle(world)

    start_sieges(world, SCENARIO)

    assert len(world.sieges) == 1
    assert world.sieges[0].army_ids == ["army_ashford_1", "army_ashford_2"]


def test_existing_siege_is_not_duplicated() -> None:
    world = make_siege_world()
    add_resolved_battle(world)

    start_sieges(world, SCENARIO)
    second = start_sieges(world, SCENARIO)

    assert len(world.sieges) == 1
    assert second == []
    assert TARGET_OWNER != BESIEGER
