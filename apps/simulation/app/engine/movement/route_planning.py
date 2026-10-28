import dataclasses
from dataclasses import dataclass

from app.engine.movement.knowledge import known_hazards
from app.engine.movement.reasons import RejectReason
from app.engine.movement.route_options import (
    RoutePreferences,
    plan_route,
    preferred_cost,
)
from app.engine.movement.state import MovementRun
from app.models.world_army import ArmyState, MarchState
from strategy_contracts.ids import RegionId


@dataclass(frozen=True)
class MarchPlan:
    route: list[RegionId]
    is_returning: bool = False


@dataclass(frozen=True)
class PlanningScope:
    run: MovementRun
    army: ArmyState
    preferences: RoutePreferences
    hazards: frozenset[RegionId]

    def route(
        self, start: RegionId, goal: RegionId, also_avoid: set[RegionId]
    ) -> list[RegionId] | None:
        preferences = dataclasses.replace(
            self.preferences, avoid=self.preferences.avoid | also_avoid
        )
        return plan_route(
            self.run.index, self.run.tuning, start, goal, preferences, self.hazards
        )


def _cost(scope: PlanningScope, start: RegionId, route: list[RegionId]) -> int:
    run = scope.run
    return preferred_cost(
        run.index, run.tuning, start, route, scope.preferences, scope.hazards
    )


def _forward_plan(
    scope: PlanningScope, march: MarchState, destination: RegionId
) -> tuple[int, MarchPlan] | None:
    onward = scope.route(march.to_id, destination, {scope.army.location_id})
    if onward is None:
        return None
    route = [march.to_id, *onward]
    cost = max(0, _cost(scope, march.from_id, route) - march.leg_progress)
    return cost, MarchPlan(route)


def _backward_plan(
    scope: PlanningScope, march: MarchState, destination: RegionId
) -> tuple[int, MarchPlan] | None:
    location = scope.army.location_id
    if destination == location:
        return march.leg_progress, MarchPlan([], is_returning=True)
    route = scope.route(location, destination, {march.to_id})
    if route is None:
        return None
    return march.leg_progress + _cost(scope, location, route), MarchPlan(
        route, is_returning=True
    )


def _plan_mid_leg(
    scope: PlanningScope, march: MarchState, destination: RegionId
) -> MarchPlan | RejectReason:
    # NOTE: forward is listed first so an exact tie keeps going rather than turning back.
    options = [
        option
        for option in (
            _forward_plan(scope, march, destination),
            _backward_plan(scope, march, destination),
        )
        if option is not None
    ]
    if not options:
        return RejectReason.NO_ROUTE
    return min(options, key=lambda option: option[0])[1]


def plan_march(
    run: MovementRun,
    army: ArmyState,
    destination: RegionId,
    preferences: RoutePreferences,
) -> MarchPlan | RejectReason:
    if destination not in run.index.terrain:
        return RejectReason.UNKNOWN_REGION
    if destination in preferences.avoid:
        return RejectReason.AVOID_BLOCKS_GOAL
    hazards = known_hazards(run.world, army.owner_id, run.index)
    scope = PlanningScope(run, army, preferences, hazards)
    march = army.march
    if march is not None and march.leg_progress > 0:
        return _plan_mid_leg(scope, march, destination)
    if destination == army.location_id:
        return RejectReason.ALREADY_THERE
    route = scope.route(army.location_id, destination, set())
    return MarchPlan(route) if route else RejectReason.NO_ROUTE
