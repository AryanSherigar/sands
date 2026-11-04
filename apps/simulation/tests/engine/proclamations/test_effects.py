import pytest
from app.engine.proclamations.effects import (
    calculate_proclamation_deltas,
    scale_by_per_mille,
)
from strategy_contracts.proclamation import (
    ProclamationBurden,
    ProclamationDomain,
)


def test_martial_levies_moderate_effects() -> None:
    immediate, ongoing = calculate_proclamation_deltas(
        ProclamationDomain.MARTIAL_LEVIES,
        ProclamationBurden.MODERATE,
    )
    assert immediate == {"manpower": 200, "gold": -50, "unrest": 5}
    assert ongoing == {"manpower_regen_percent": 25, "unrest_per_turn": 3}


def test_emergency_taxation_effects() -> None:
    immediate, ongoing = calculate_proclamation_deltas(
        ProclamationDomain.EMERGENCY_TAXATION,
        ProclamationBurden.MODERATE,
    )
    assert immediate["gold"] > 0
    assert immediate["unrest"] > 0
    assert ongoing["tax_percent_points"] > 0
    assert ongoing["trade_efficiency_percent"] < 0


def test_burden_multipliers_scale_properly() -> None:
    imm_light, on_light = calculate_proclamation_deltas(
        ProclamationDomain.EMERGENCY_TAXATION,
        ProclamationBurden.LIGHT,
    )
    imm_rad, on_rad = calculate_proclamation_deltas(
        ProclamationDomain.EMERGENCY_TAXATION,
        ProclamationBurden.RADICAL,
    )
    assert imm_rad["gold"] > imm_light["gold"]
    assert on_rad["tax_percent_points"] > on_light["tax_percent_points"]


def test_every_effect_is_a_whole_number() -> None:
    for domain in ProclamationDomain:
        for burden in ProclamationBurden:
            immediate, ongoing = calculate_proclamation_deltas(domain, burden)
            values = [*immediate.values(), *ongoing.values()]
            assert all(type(value) is int for value in values)


@pytest.mark.parametrize(
    ("value", "per_mille", "expected"),
    [(5, 500, 3), (-5, 500, -3), (3, 1750, 5), (-3, 1750, -5), (10, 1000, 10)],
)
def test_scaling_rounds_half_away_from_zero_for_both_signs(
    value: int, per_mille: int, expected: int
) -> None:
    assert scale_by_per_mille(value, per_mille) == expected
