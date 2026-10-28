from collections.abc import Callable
from dataclasses import replace

from app.engine.ai.candidates import ScoredCandidate
from app.engine.logistics.supply import supply_assessments
from app.engine.outrage.effects import rage_steps
from app.models.orders import AttackOrder, MoveArmyOrder
from app.models.world_state import WorldState
from strategy_contracts.battle import SupplyState
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory

Rescorer = Callable[
    [WorldState, StrategyScenario, FactionId, list[ScoredCandidate]],
    list[ScoredCandidate],
]


def _destination(item: ScoredCandidate) -> RegionId | None:
    order = item.candidate.order
    if isinstance(order, MoveArmyOrder):
        return order.to_region_id
    if isinstance(order, AttackOrder):
        return order.target_region_id
    return None


def supply_rescorer(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    scored: list[ScoredCandidate],
) -> list[ScoredCandidate]:
    if not any(_destination(item) is not None for item in scored):
        return scored
    tuning = scenario.tuning.ai
    penalties = {
        SupplyState.STRAINED: tuning.supply_strained_penalty,
        SupplyState.ISOLATED: tuning.supply_isolated_penalty,
    }
    assessments = supply_assessments(world, scenario)
    result: list[ScoredCandidate] = []
    for item in scored:
        region_id = _destination(item)
        assessment = assessments.get((faction_id, region_id or ""))
        penalty = 0 if assessment is None else penalties.get(assessment.state, 0)
        result.append(
            replace(
                item,
                score=item.score - penalty,
                adjustment=item.adjustment - penalty,
            )
        )
    return result


DEFENSIVE_CATEGORIES = (ScoreCategory.BUILD, ScoreCategory.HOARD)


def _rage_adjustment(
    category: ScoreCategory, steps: int, scenario: StrategyScenario
) -> int:
    tuning = scenario.tuning.outrage
    if category == ScoreCategory.ATTACK:
        return tuning.ai_attack_boost * steps
    if category in DEFENSIVE_CATEGORIES:
        return -tuning.ai_defense_penalty * steps
    return 0


def outrage_rescorer(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    scored: list[ScoredCandidate],
) -> list[ScoredCandidate]:
    steps = rage_steps(world, scenario, faction_id)
    if steps == 0:
        return scored
    result: list[ScoredCandidate] = []
    for item in scored:
        shift = _rage_adjustment(item.candidate.category, steps, scenario)
        result.append(
            replace(item, score=item.score + shift, adjustment=item.adjustment + shift)
        )
    return result


RESCORERS: tuple[Rescorer, ...] = (supply_rescorer, outrage_rescorer)


def rescore(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    scored: list[ScoredCandidate],
) -> list[ScoredCandidate]:
    for rescorer in RESCORERS:
        scored = rescorer(world, scenario, faction_id, scored)
    return scored
