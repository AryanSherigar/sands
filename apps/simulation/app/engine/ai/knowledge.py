from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass

from app.engine.movement.knowledge import visible_regions
from app.engine.movement.map_index import MapIndex, build_map_index
from app.models.world_army import ArmyState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import StrategyScenario


@dataclass(frozen=True)
class Knowledge:
    index: MapIndex
    visible: frozenset[RegionId]
    owners: Mapping[RegionId, FactionId | None]
    garrisons: Mapping[RegionId, int]


def build_knowledge(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> Knowledge:
    index = build_map_index(scenario.map)
    visible = visible_regions(world, faction_id, index)
    owners: dict[RegionId, FactionId | None] = {}
    garrisons: dict[RegionId, int] = {}
    for region_id, intel in sorted(world.factions[faction_id].intel.items()):
        owners[region_id] = intel.owner_id
        garrisons[region_id] = intel.garrison_high
    for region_id in sorted(visible):
        if region_id in world.regions:
            owners[region_id] = world.regions[region_id].owner_id
    return Knowledge(index, visible, owners, garrisons)


def known_foreign_armies(
    world: WorldState, faction_id: FactionId, knowledge: Knowledge
) -> list[ArmyState]:
    return [
        army
        for _, army in sorted(world.armies.items())
        if army.owner_id != faction_id and army.location_id in knowledge.visible
    ]


def region_distances(index: MapIndex, start: RegionId) -> dict[RegionId, int]:
    distances = {start: 0}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for neighbor in sorted(index.neighbors.get(current, frozenset())):
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    return distances
