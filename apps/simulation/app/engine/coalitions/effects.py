from app.engine.coalitions.registry import is_member_against
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def coalition_shift(
    world: WorldState,
    scenario: StrategyScenario,
    proposer_id: FactionId,
    counterpart_id: FactionId,
) -> int:
    if world.coalition_ruleset < 1:
        return 0
    if not is_member_against(world, counterpart_id, proposer_id):
        return 0
    return scenario.tuning.coalition.peace_shift
