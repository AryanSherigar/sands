import pytest
from app.models.world_region import OccupationState
from strategy_contracts.enums import TaxRate

from tests.engine.economy.builders import (
    PLAYER,
    RIVAL,
    events_of,
    make_faction,
    make_region,
    make_world,
    run_economy,
)


def _unrest_after(rate: TaxRate, unrest: int) -> int:
    world = make_world(
        regions=[make_region("home", PLAYER, unrest=unrest)],
        factions=[make_faction(PLAYER, tax_rate=rate)],
    )
    return run_economy(world).world.regions["home"].unrest


@pytest.mark.parametrize(
    ("rate", "expected"),
    [(TaxRate.LOW, 17), (TaxRate.NORMAL, 19), (TaxRate.HIGH, 23)],
)
def test_tax_rate_moves_unrest_every_turn(rate: TaxRate, expected: int) -> None:
    assert _unrest_after(rate, 20) == expected


def test_unrest_never_goes_below_zero() -> None:
    assert _unrest_after(TaxRate.LOW, 1) == 0


def test_unrest_never_goes_above_one_hundred() -> None:
    assert _unrest_after(TaxRate.HIGH, 99) == 100


def test_a_region_that_does_not_move_logs_nothing() -> None:
    world = make_world(
        regions=[make_region("home", PLAYER, unrest=0)],
        factions=[make_faction(PLAYER, tax_rate=TaxRate.NORMAL)],
    )
    assert events_of(run_economy(world), "unrest_drifted") == []


def test_an_occupied_region_keeps_its_unrest() -> None:
    occupied = make_region(
        "home",
        PLAYER,
        unrest=40,
        occupation=OccupationState(occupier_id=RIVAL, siege_progress=0),
    )
    world = make_world(regions=[occupied], factions=[make_faction(PLAYER)])
    assert run_economy(world).world.regions["home"].unrest == 40


def test_income_is_taken_before_this_turns_drift() -> None:
    world = make_world(
        regions=[make_region("home", PLAYER, wealth=100, unrest=10)],
        factions=[make_faction(PLAYER, treasury=0, tax_rate=TaxRate.HIGH)],
    )
    assert run_economy(world).world.factions[PLAYER].treasury == 135
