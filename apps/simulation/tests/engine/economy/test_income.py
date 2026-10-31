import pytest
from app.engine.economy.income import faction_income, region_income
from app.models.world_region import OccupationState
from strategy_contracts.enums import TaxRate

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


@pytest.mark.parametrize(
    ("tax_percent", "unrest", "expected"),
    [(100, 0, 100), (100, 20, 80), (150, 0, 150), (60, 50, 30), (100, 100, 0)],
)
def test_region_income_is_wealth_times_tax_times_calm(
    tax_percent: int, unrest: int, expected: int
) -> None:
    region = make_region("home", PLAYER, wealth=100, unrest=unrest)
    assert region_income(region, tax_percent) == expected


def test_an_occupied_region_pays_nothing() -> None:
    region = make_region(
        "home",
        PLAYER,
        occupation=OccupationState(occupier_id=RIVAL, siege_progress=0),
    )
    assert region_income(region, 100) == 0


def test_income_counts_only_the_factions_own_regions() -> None:
    world = make_world(
        regions=[
            make_region("a1", PLAYER, wealth=40),
            make_region("a2", PLAYER, wealth=60),
            make_region("b1", RIVAL, wealth=500),
            make_region("free", None, wealth=500),
        ],
        factions=[make_faction(PLAYER), make_faction(RIVAL)],
    )
    report = faction_income(world, TUNING, PLAYER)
    assert report.by_region == {"a1": 40, "a2": 60}
    assert report.total == 100


def test_tax_rate_scales_income() -> None:
    totals = {}
    for rate in TaxRate:
        world = make_world(
            regions=[make_region("home", PLAYER, wealth=100)],
            factions=[make_faction(PLAYER, tax_rate=rate)],
        )
        totals[rate] = faction_income(world, TUNING, PLAYER).total
    assert totals[TaxRate.LOW] < totals[TaxRate.NORMAL] < totals[TaxRate.HIGH]


def test_the_phase_adds_income_and_logs_where_it_came_from() -> None:
    world = make_world(
        regions=[make_region("a1", PLAYER, wealth=40), make_region("a2", PLAYER)],
        factions=[make_faction(PLAYER, treasury=10)],
    )
    result = run_economy(world)
    [event] = events_of(result, "income_collected")
    assert result.world.factions[PLAYER].treasury == 150
    assert event.cause.inputs["income_a1"] == 40
    assert event.cause.inputs["income_a2"] == 100
    assert event.changes[0].before == 10
    assert event.changes[0].after == 150


def test_an_occupied_region_is_named_in_the_income_event() -> None:
    occupied = make_region(
        "lost", PLAYER, occupation=OccupationState(occupier_id=RIVAL, siege_progress=1)
    )
    world = make_world(
        regions=[make_region("home", PLAYER), occupied],
        factions=[make_faction(PLAYER)],
    )
    [event] = events_of(run_economy(world), "income_collected")
    assert "lost" in event.cause.subject_ids
    assert event.cause.inputs["regions_occupied"] == 1
    assert "income_lost" not in event.cause.inputs
