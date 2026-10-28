from collections.abc import Mapping
from dataclasses import dataclass

from strategy_contracts.enums import Terrain
from strategy_contracts.ids import RegionId
from strategy_contracts.map import MapDocument


@dataclass(frozen=True)
class MapIndex:
    terrain: Mapping[RegionId, Terrain]
    neighbors: Mapping[RegionId, frozenset[RegionId]]
    roads: frozenset[tuple[RegionId, RegionId]]

    def has_road(self, left: RegionId, right: RegionId) -> bool:
        return tuple(sorted((left, right))) in self.roads


def build_map_index(map_document: MapDocument) -> MapIndex:
    terrain = {region.id: region.terrain for region in map_document.regions}
    neighbors: dict[RegionId, set[RegionId]] = {
        region_id: set() for region_id in terrain
    }
    for region in map_document.regions:
        for neighbor_id in region.neighbor_ids:
            if neighbor_id in neighbors:
                neighbors[region.id].add(neighbor_id)
                neighbors[neighbor_id].add(region.id)
    roads = frozenset(
        (min(road.region_a, road.region_b), max(road.region_a, road.region_b))
        for road in map_document.roads
    )
    return MapIndex(
        terrain=terrain,
        neighbors={region_id: frozenset(ids) for region_id, ids in neighbors.items()},
        roads=roads,
    )
