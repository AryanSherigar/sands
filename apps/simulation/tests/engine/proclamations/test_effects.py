from app.engine.proclamations.effects import calculate_proclamation_deltas
from strategy_contracts.proclamation import (
    ProclamationBurden,
    ProclamationDomain,
)


def test_martial_levies_moderate_effects() -> None:
    immediate, ongoing = calculate_proclamation_deltas(
        ProclamationDomain.MARTIAL_LEVIES,
        ProclamationBurden.MODERATE,
    )
    assert immediate["manpower"] > 0
    assert immediate["gold"] < 0
    assert ongoing["manpower_regen_delta"] > 0
    assert ongoing["unrest_delta"] > 0


def test_emergency_taxation_effects() -> None:
    immediate, ongoing = calculate_proclamation_deltas(
        ProclamationDomain.EMERGENCY_TAXATION,
        ProclamationBurden.MODERATE,
    )
    assert immediate["gold"] > 0
    assert immediate["unrest"] > 0
    assert ongoing["tax_rate_delta"] > 0
    assert ongoing["wealth_growth_delta"] < 0


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
    assert on_rad["tax_rate_delta"] > on_light["tax_rate_delta"]
