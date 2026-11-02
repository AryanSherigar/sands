from app.engine.diplomacy.grounds import is_usable
from app.models.api_world_view import GroundView
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def project_usable_grounds(
    world: WorldState, faction_id: FactionId, scenario: StrategyScenario
) -> list[GroundView]:
    """Grounds the player may declare war on now; strength and thresholds stay hidden."""
    return [
        GroundView(
            id=ground.id,
            kind=ground.kind,
            target_faction_id=ground.target_faction_id,
            region_id=ground.region_id,
        )
        for ground in sorted(world.grounds, key=lambda item: item.id)
        if ground.holder_faction_id == faction_id and is_usable(world, scenario, ground)
    ]
