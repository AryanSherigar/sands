from app.engine.proclamations.constants import (
    BASE_IMMEDIATE_EFFECTS,
    BASE_ONGOING_MODIFIERS,
    BURDEN_PER_MILLE,
    PER_MILLE,
)
from strategy_contracts.proclamation import ProclamationBurden, ProclamationDomain

HALF_PER_MILLE = PER_MILLE // 2


def scale_by_per_mille(value: int, per_mille: int) -> int:
    """Rounds half away from zero so a penalty and a bonus scale symmetrically."""
    sign = -1 if value < 0 else 1
    return sign * ((abs(value) * per_mille + HALF_PER_MILLE) // PER_MILLE)


def _scale(base: dict[str, int], per_mille: int) -> dict[str, int]:
    return {key: scale_by_per_mille(value, per_mille) for key, value in base.items()}


def calculate_proclamation_deltas(
    domain: ProclamationDomain, burden: ProclamationBurden
) -> tuple[dict[str, int], dict[str, int]]:
    per_mille = BURDEN_PER_MILLE.get(burden, PER_MILLE)
    immediate = _scale(BASE_IMMEDIATE_EFFECTS.get(domain, {}), per_mille)
    ongoing = _scale(BASE_ONGOING_MODIFIERS.get(domain, {}), per_mille)
    return immediate, ongoing
