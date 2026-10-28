from app.engine.trait_axes import axis_totals
from app.models.world_character import LeaderState
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.outrage import OutrageTuning
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import OutrageLevel
from strategy_contracts.traits import TraitAxis

LADDER = tuple(OutrageLevel)


def demand_price_percent(
    *, demand: int, demander_score: int, tuning: OutrageTuning
) -> int:
    score = max(demander_score, tuning.min_demander_score)
    return demand * FULL_SHARE_PERCENT // score


def temper_total(leader: LeaderState, scenario: StrategyScenario) -> int:
    totals = axis_totals(leader, scenario)
    return (
        totals[TraitAxis.PRIDE]
        + totals[TraitAxis.AGGRESSION]
        - totals[TraitAxis.CAUTION]
    )


def _trait_step(temper: int, tuning: OutrageTuning) -> int:
    if temper >= tuning.trait_shift_total:
        return 1
    if temper <= -tuning.trait_shift_total:
        return -1
    return 0


def _tone_step(tone_grade: int | None, tuning: OutrageTuning) -> int:
    if tone_grade is None:
        return 0
    if tone_grade >= tuning.tone_worsen_at:
        return 1
    if tone_grade <= tuning.tone_soften_at:
        return -1
    return 0


def outrage_level(
    price_percent: int,
    temper: int,
    tone_grade: int | None,
    tuning: OutrageTuning,
) -> OutrageLevel:
    thresholds = tuning.level_thresholds_percent
    base = sum(1 for threshold in thresholds if price_percent >= threshold)
    shifted = base + _trait_step(temper, tuning) + _tone_step(tone_grade, tuning)
    return LADDER[max(0, min(len(LADDER) - 1, shifted))]
