from app.engine.pressure.strain import compute_strain
from app.engine.pressure.will import compute_will
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def is_war_weary(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> bool:
    tuning = scenario.tuning.overtures
    strain = compute_strain(world, scenario, faction_id).value
    will = compute_will(world, scenario, faction_id).value
    return (
        strain >= tuning.peace_offer_min_strain or will <= tuning.peace_offer_max_will
    )
