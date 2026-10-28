from collections import Counter

from app.engine.trait_axes import axis_totals
from app.models.world_character import LeaderState
from strategy_contracts.ids import StanceId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory, StanceDefinition
from strategy_contracts.traits import TraitAxis

CATEGORY_AXIS_AFFINITY: dict[ScoreCategory, dict[TraitAxis, int]] = {
    ScoreCategory.ATTACK: {
        TraitAxis.AGGRESSION: 2,
        TraitAxis.PRIDE: 1,
        TraitAxis.CAUTION: -1,
    },
    ScoreCategory.EXPAND: {
        TraitAxis.AGGRESSION: 1,
        TraitAxis.GREED: 1,
        TraitAxis.PRIDE: 1,
    },
    ScoreCategory.BUILD: {TraitAxis.CAUTION: 1, TraitAxis.GREED: 1},
    ScoreCategory.ALLY: {TraitAxis.TRUST: 2, TraitAxis.HONOR: 1},
    ScoreCategory.HOARD: {
        TraitAxis.GREED: 2,
        TraitAxis.CAUTION: 1,
        TraitAxis.TRUST: -1,
    },
}


def fallback_stance_id(
    leader: LeaderState, menu: list[StanceDefinition], scenario: StrategyScenario
) -> StanceId:
    totals = axis_totals(leader, scenario)
    best = max(
        enumerate(menu),
        key=lambda item: (_stance_score(item[1], totals), -item[0]),
    )
    return best[1].id


def _stance_score(stance: StanceDefinition, axis_totals: Counter[TraitAxis]) -> int:
    return sum(
        shift * category_affinity(category, axis_totals)
        for category, shift in stance.shifts.items()
    )


def category_affinity(category: ScoreCategory, axis_totals: Counter[TraitAxis]) -> int:
    weights = CATEGORY_AXIS_AFFINITY[category]
    return sum(axis_totals[axis] * weight for axis, weight in weights.items())
