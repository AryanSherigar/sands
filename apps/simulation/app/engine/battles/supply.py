from app.engine.logistics.supply import supply_assessment
from app.models.world_state import WorldState
from strategy_contracts.battle import SupplyState
from strategy_contracts.scenario import StrategyScenario


def supply_state(
    world: WorldState, region_id: str, faction_id: str, scenario: StrategyScenario
) -> SupplyState:
    """Classify one contingent through the shared campaign supply rules."""
    return supply_assessment(world, region_id, faction_id, scenario).state
