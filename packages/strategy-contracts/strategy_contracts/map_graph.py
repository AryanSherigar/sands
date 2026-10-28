from collections import Counter

from strategy_contracts.ids import RegionId
from strategy_contracts.map import MapDocument


def build_neighbor_graph(
    map_document: MapDocument,
) -> dict[RegionId, frozenset[RegionId]]:
    return {
        region.id: frozenset(region.neighbor_ids) for region in map_document.regions
    }


def find_one_way_links(map_document: MapDocument) -> list[tuple[RegionId, RegionId]]:
    graph = build_neighbor_graph(map_document)
    one_way = [
        (region_id, neighbor_id)
        for region_id, neighbor_ids in graph.items()
        for neighbor_id in neighbor_ids
        if neighbor_id in graph and region_id not in graph[neighbor_id]
    ]
    return sorted(one_way)


def find_duplicate_region_ids(map_document: MapDocument) -> list[RegionId]:
    counts = Counter(region.id for region in map_document.regions)
    return sorted(region_id for region_id, count in counts.items() if count > 1)


def _undirected_adjacency(map_document: MapDocument) -> dict[RegionId, set[RegionId]]:
    adjacency: dict[RegionId, set[RegionId]] = {
        region.id: set() for region in map_document.regions
    }
    for region_id, neighbor_ids in build_neighbor_graph(map_document).items():
        for neighbor_id in neighbor_ids:
            if neighbor_id in adjacency:
                adjacency[region_id].add(neighbor_id)
                adjacency[neighbor_id].add(region_id)
    return adjacency


def _collect_group(
    start_id: RegionId, adjacency: dict[RegionId, set[RegionId]]
) -> frozenset[RegionId]:
    seen = {start_id}
    stack = [start_id]
    while stack:
        current = stack.pop()
        unseen = adjacency[current] - seen
        seen |= unseen
        stack.extend(unseen)
    return frozenset(seen)


def find_disconnected_groups(map_document: MapDocument) -> list[frozenset[RegionId]]:
    adjacency = _undirected_adjacency(map_document)
    groups: list[frozenset[RegionId]] = []
    visited: set[RegionId] = set()
    for region_id in sorted(adjacency):
        if region_id in visited:
            continue
        group = _collect_group(region_id, adjacency)
        visited |= group
        groups.append(group)
    return groups if len(groups) > 1 else []
