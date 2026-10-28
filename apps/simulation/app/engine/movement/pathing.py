import heapq
from collections.abc import Mapping
from dataclasses import dataclass, field

from app.engine.movement.costs import route_base_cost
from app.engine.movement.map_index import MapIndex
from strategy_contracts.ids import RegionId
from strategy_contracts.scenario import MovementTuning

Route = tuple[RegionId, ...]
Candidate = tuple[int, Route]


@dataclass(frozen=True)
class RouteExtras:
    entry_penalties: Mapping[RegionId, int] = field(default_factory=dict)
    off_road_penalty: int = 0

    def leg_penalty(self, index: MapIndex, left: RegionId, right: RegionId) -> int:
        penalty = self.entry_penalties.get(right, 0)
        if not index.has_road(left, right):
            penalty += self.off_road_penalty
        return penalty


def _extend(
    index: MapIndex,
    tuning: MovementTuning,
    candidate: Candidate,
    start: RegionId,
    avoid: frozenset[RegionId],
    extras: RouteExtras,
) -> list[Candidate]:
    cost, route = candidate
    current = route[-1] if route else start
    blocked = {start, *route, *avoid}
    return [
        (
            cost
            + route_base_cost(index, tuning, current, neighbor_id)
            + extras.leg_penalty(index, current, neighbor_id),
            (*route, neighbor_id),
        )
        for neighbor_id in sorted(index.neighbors[current] - blocked)
    ]


def find_route(
    index: MapIndex,
    tuning: MovementTuning,
    start: RegionId,
    goal: RegionId,
    avoid: frozenset[RegionId] = frozenset(),
    extras: RouteExtras | None = None,
) -> list[RegionId] | None:
    """Cheapest route start -> goal, excluding `start`; ties go to the lowest ids.

    Candidates compare as (cost, route), so among equal-cost routes the one that is
    lexicographically smallest by region id wins, whatever order links were listed.
    """
    extras = extras or RouteExtras()
    if start not in index.terrain or goal not in index.terrain or goal in avoid:
        return None
    if start == goal:
        return []
    best: dict[RegionId, Candidate] = {}
    queue: list[Candidate] = [(0, ())]
    while queue:
        candidate = heapq.heappop(queue)
        route = candidate[1]
        if route and route[-1] == goal:
            return list(route)
        if route and best[route[-1]] != candidate:
            continue
        for extended in _extend(index, tuning, candidate, start, avoid, extras):
            region_id = extended[1][-1]
            if region_id not in best or extended < best[region_id]:
                best[region_id] = extended
                heapq.heappush(queue, extended)
    return None
