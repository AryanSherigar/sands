from app.engine.proclamations.constants import (
    BASE_IMMEDIATE_EFFECTS,
    BASE_ONGOING_MODIFIERS,
    BURDEN_FACTORS,
)
from strategy_contracts.proclamation import ProclamationBurden, ProclamationDomain


def _scale_immediate(base: dict[str, int], factor: float) -> dict[str, int]:
    return {k: round(v * factor) for k, v in base.items()}


def _scale_ongoing(base: dict[str, float], factor: float) -> dict[str, float]:
    return {k: round(v * factor, 4) for k, v in base.items()}


def calculate_proclamation_deltas(
    domain: ProclamationDomain, burden: ProclamationBurden
) -> tuple[dict[str, int], dict[str, float]]:
    factor = BURDEN_FACTORS.get(burden, 1.0)
    base_immediate = BASE_IMMEDIATE_EFFECTS.get(domain, {})
    base_ongoing = BASE_ONGOING_MODIFIERS.get(domain, {})
    scaled_immediate = _scale_immediate(base_immediate, factor)
    scaled_ongoing = _scale_ongoing(base_ongoing, factor)
    return scaled_immediate, scaled_ongoing
