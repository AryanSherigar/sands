from app.engine.ai.candidates import Candidate, ScoredCandidate
from app.engine.stances.fallback import category_affinity
from app.engine.stances.menu import resolve_stance_menu
from app.engine.trait_axes import axis_totals
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory


def score_candidate(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    candidate: Candidate,
) -> ScoredCandidate:
    traits = trait_score(world, scenario, faction_id, candidate.category)
    stance = stance_score(world, scenario, faction_id, candidate.category)
    aim = aim_score(world, scenario, faction_id, candidate)
    return ScoredCandidate(
        candidate=candidate,
        score=candidate.base_score + traits + stance + aim,
        trait_score=traits,
        stance_score=stance,
        aim_score=aim,
    )


def aim_score(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    candidate: Candidate,
) -> int:
    aim = world.aims.get(faction_id)
    if aim is None:
        return 0
    tuning = scenario.tuning.ai
    score = tuning.aim_bonus if aim.category == candidate.category else 0
    target_id = getattr(candidate.order, "target_faction_id", None)
    if aim.target_faction_id is not None and target_id == aim.target_faction_id:
        score += tuning.aim_target_bonus
    return score


def trait_score(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    category: ScoreCategory,
) -> int:
    leader_id = world.factions[faction_id].leader_id
    if leader_id is None or leader_id not in world.leaders:
        return 0
    totals = axis_totals(world.leaders[leader_id], scenario)
    return category_affinity(category, totals) * scenario.tuning.ai.trait_weight


def stance_score(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    category: ScoreCategory,
) -> int:
    faction = world.factions[faction_id]
    if faction.leader_id is None or faction.stance.option_id is None:
        return 0
    menu = resolve_stance_menu(scenario, faction_id)
    stance = next((item for item in menu if item.id == faction.stance.option_id), None)
    if stance is None:
        return 0
    return stance.shifts.get(category, 0) * scenario.tuning.ai.stance_weight
