from app.engine.movement.knowledge import visible_regions
from app.engine.movement.map_index import build_map_index
from app.models.world_region import RegionIntel
from app.models.world_state import CURRENT_VISIBILITY_RULESET, WorldState
from strategy_contracts.scenario import StrategyScenario

GARRISON_ESTIMATE_MARGIN = 10


def record_visible_observations(world: WorldState, scenario: StrategyScenario) -> None:
    if world.visibility_ruleset != CURRENT_VISIBILITY_RULESET:
        return
    index = build_map_index(scenario.map)
    for faction_id in sorted(world.factions):
        _record_faction_observations(
            world, faction_id, visible_regions(world, faction_id, index)
        )


def _record_faction_observations(
    world: WorldState, faction_id: str, visible: frozenset[str]
) -> None:
    intel = world.factions[faction_id].intel
    for region_id in sorted(visible):
        region = world.regions[region_id]
        observation = RegionIntel(
            last_seen_turn=world.clock.turn,
            owner_id=region.owner_id,
            garrison_low=max(0, region.garrison - GARRISON_ESTIMATE_MARGIN),
            garrison_high=region.garrison + GARRISON_ESTIMATE_MARGIN,
        )
        if intel.get(region_id) != observation:
            intel[region_id] = observation
