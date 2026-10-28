import itertools
from dataclasses import dataclass

from app.engine.movement.costs import route_total_cost
from app.engine.movement.map_index import MapIndex
from app.engine.movement.pathing import RouteExtras, find_route
from strategy_contracts.enums import RouteStyle
from strategy_contracts.ids import RegionId
from strategy_contracts.scenario import MovementTuning


@dataclass(frozen=True)
class RoutePreferences:
    style: RouteStyle = RouteStyle.FASTEST
    via: tuple[RegionId, ...] = ()
    avoid: frozenset[RegionId] = frozenset()


def extras_for(
    style: RouteStyle, tuning: MovementTuning, hazards: frozenset[RegionId]
) -> RouteExtras:
    if style is RouteStyle.SAFEST:
        penalties = dict.fromkeys(hazards, tuning.safest_hazard_penalty)
        return RouteExtras(entry_penalties=penalties)
    if style is RouteStyle.ROADS:
        return RouteExtras(off_road_penalty=tuning.roads_off_road_penalty)
    return RouteExtras()


def _stops(
    start: RegionId, goal: RegionId, via: tuple[RegionId, ...]
) -> list[RegionId]:
    waypoints = [region_id for region_id in via if region_id not in (start, goal)]
    return [start, *waypoints, goal]


def plan_route(
    index: MapIndex,
    tuning: MovementTuning,
    start: RegionId,
    goal: RegionId,
    preferences: RoutePreferences,
    hazards: frozenset[RegionId],
) -> list[RegionId] | None:
    extras = extras_for(preferences.style, tuning, hazards)
    route: list[RegionId] = []
    for left, right in itertools.pairwise(_stops(start, goal, preferences.via)):
        behind = frozenset({start, *route} - {left})
        leg = find_route(index, tuning, left, right, preferences.avoid | behind, extras)
        if leg is None:
            return None
        route += leg
    return route


def preferred_cost(
    index: MapIndex,
    tuning: MovementTuning,
    start: RegionId,
    route: list[RegionId],
    preferences: RoutePreferences,
    hazards: frozenset[RegionId],
) -> int:
    extras = extras_for(preferences.style, tuning, hazards)
    stops = [start, *route]
    penalty = sum(
        extras.leg_penalty(index, left, right)
        for left, right in itertools.pairwise(stops)
    )
    return route_total_cost(index, tuning, start, route) + penalty
