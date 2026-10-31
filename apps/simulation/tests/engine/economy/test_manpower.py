from app.engine.economy.manpower import faction_manpower, region_refill
from app.models.world_region import ImprovementState, OccupationState
from strategy_contracts.enums import ImprovementKind

from tests.engine.economy.builders import (
    PLAYER,
    RIVAL,
    TEST_TUNING,
    events_of,
    make_faction,
    make_region,
    make_world,
    run_economy,
)

TUNING = TEST_TUNING


def test_a_region_refills_a_share_of_its_population() -> None:
    region = make_region("home", PLAYER, population=500, manpower=0)
    assert region_refill(region, TUNING) == 10


def test_refill_stops_at_the_cap() -> None:
    region = make_region("home", PLAYER, population=500, manpower=95)
    assert region_refill(region, TUNING) == 5


def test_a_full_region_refills_nothing() -> None:
    region = make_region("home", PLAYER, population=500, manpower=100)
    assert region_refill(region, TUNING) == 0


def test_a_tiny_population_still_refills_one() -> None:
    region = make_region("home", PLAYER, population=10, manpower=0)
    assert region_refill(region, TUNING) == 1


def test_a_finished_barracks_refills_faster() -> None:
    barracks = ImprovementState(kind=ImprovementKind.BARRACKS, turns_remaining=0)
    region = make_region(
        "home", PLAYER, population=500, manpower=0, improvements=[barracks]
    )
    assert region_refill(region, TUNING) == 15


def test_a_barracks_under_construction_does_nothing_yet() -> None:
    barracks = ImprovementState(kind=ImprovementKind.BARRACKS, turns_remaining=2)
    region = make_region(
        "home", PLAYER, population=500, manpower=0, improvements=[barracks]
    )
    assert region_refill(region, TUNING) == 10


def test_an_occupied_region_refills_nothing() -> None:
    region = make_region(
        "home",
        PLAYER,
        manpower=0,
        occupation=OccupationState(occupier_id=RIVAL, siege_progress=0),
    )
    assert region_refill(region, TUNING) == 0


def test_faction_manpower_is_the_sum_of_its_regions() -> None:
    world = make_world(
        regions=[
            make_region("a1", PLAYER, manpower=30),
            make_region("a2", PLAYER, manpower=12),
            make_region("b1", RIVAL, manpower=500),
        ],
        factions=[make_faction(PLAYER), make_faction(RIVAL)],
    )
    assert faction_manpower(world, PLAYER) == 42


def test_the_phase_refills_each_region_and_logs_it() -> None:
    world = make_world(
        regions=[make_region("a1", PLAYER, manpower=0)],
        factions=[make_faction(PLAYER)],
    )
    result = run_economy(world)
    [event] = events_of(result, "manpower_refilled")
    assert result.world.regions["a1"].manpower == 10
    assert event.cause.inputs == {"gain_a1": 10}
