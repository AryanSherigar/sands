from app.engine.succession.crisis import crisis_of
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def _is_in_penalty(world: WorldState, faction_id: FactionId) -> bool:
    crisis = crisis_of(world, faction_id)
    return crisis is not None and crisis.is_penalty_active


def crisis_stability_loss(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    if not _is_in_penalty(world, faction_id):
        return 0
    return scenario.tuning.succession.crisis_stability_loss


def crisis_unrest(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    if not _is_in_penalty(world, faction_id):
        return 0
    return scenario.tuning.succession.crisis_unrest


def crisis_acceptance_shift(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    if not _is_in_penalty(world, faction_id):
        return 0
    return scenario.tuning.succession.crisis_acceptance_shift
