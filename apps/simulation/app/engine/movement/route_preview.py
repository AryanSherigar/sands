import itertools
from collections.abc import Iterable
from dataclasses import dataclass

from app.engine.movement.contact import ContactKind, classify_entry
from app.engine.movement.costs import leg_cost, route_total_cost
from app.engine.movement.knowledge import visible_regions
from app.engine.movement.map_index import build_map_index
from app.engine.movement.reasons import RejectReason
from app.engine.movement.route_options import RoutePreferences
from app.engine.movement.route_planning import MarchPlan, plan_march
from app.engine.movement.state import MovementRun
from app.models.api_route_preview import RoutePreview, RouteWarning, WarningKind
from app.models.world_army import ArmyState
from app.models.world_state import WorldState
from strategy_contracts.enums import RouteStyle
from strategy_contracts.ids import ArmyId, RegionId
from strategy_contracts.scenario import StrategyScenario

MAX_ESTIMATED_TURNS = 60
WARNING_BY_CONTACT = {
    ContactKind.BATTLE: WarningKind.HOSTILE_ARMY,
    ContactKind.CONFRONTATION: WarningKind.CLOSED_BORDER,
    ContactKind.ENEMY_REGION: WarningKind.ENEMY_TERRITORY,
}


@dataclass(frozen=True)
class Leg:
    from_id: RegionId
    to_id: RegionId
    progress: int
    is_walk_back: bool = False


def _progress_of(army: ArmyState) -> int:
    return army.march.leg_progress if army.march else 0


def _base_cost(run: MovementRun, army: ArmyState, plan: MarchPlan) -> int:
    total = route_total_cost(run.index, run.tuning, army.location_id, plan.route)
    if plan.is_returning:
        return _progress_of(army) + total
    return max(0, total - _progress_of(army))


def _legs(army: ArmyState, plan: MarchPlan) -> list[Leg]:
    stops = [army.location_id, *plan.route]
    legs = [Leg(left, right, 0) for left, right in itertools.pairwise(stops)]
    if plan.is_returning:
        walk_back = Leg(stops[0], stops[0], _progress_of(army), is_walk_back=True)
        return [walk_back, *legs]
    if legs:
        legs[0] = Leg(legs[0].from_id, legs[0].to_id, _progress_of(army))
    return legs


def _points_needed(
    run: MovementRun, army: ArmyState, leg: Leg, progress: int, turn: int
) -> int:
    if leg.is_walk_back:
        return progress
    clock = run.world.clock.model_copy(update={"turn": run.world.clock.turn + turn})
    cost = leg_cost(run.index, army, clock, run.tuning, leg.from_id, leg.to_id)
    return max(0, cost.total - progress)


def _run_leg(
    run: MovementRun, army: ArmyState, leg: Leg, turn: int, left: int
) -> tuple[int, int]:
    progress = leg.progress
    while turn < MAX_ESTIMATED_TURNS:
        needed = _points_needed(run, army, leg, progress, turn)
        if needed <= left:
            return turn, left - needed
        progress = progress - left if leg.is_walk_back else progress + left
        turn, left = turn + 1, run.tuning.budget_per_turn
    return MAX_ESTIMATED_TURNS, 0


def _estimated_turns(run: MovementRun, army: ArmyState, plan: MarchPlan) -> int:
    turn, left = 0, run.tuning.budget_per_turn
    for leg in _legs(army, plan):
        turn, left = _run_leg(run, army, leg, turn, left)
    return min(turn + 1, MAX_ESTIMATED_TURNS)


def _warnings(
    run: MovementRun, army: ArmyState, plan: MarchPlan, visible: frozenset[RegionId]
) -> list[RouteWarning]:
    warnings = []
    for region_id in plan.route:
        kind = WARNING_BY_CONTACT.get(classify_entry(run.world, army, region_id).kind)
        if kind is not None and region_id in visible:
            warnings.append(RouteWarning(kind=kind, region_id=region_id))
    return warnings


def _plans_by_style(
    run: MovementRun,
    army: ArmyState,
    destination: RegionId,
    via: tuple[RegionId, ...],
    avoid: frozenset[RegionId],
) -> list[tuple[RouteStyle, MarchPlan]]:
    plans = []
    for style in RouteStyle:
        preferences = RoutePreferences(style=style, via=via, avoid=avoid)
        plan = plan_march(run, army, destination, preferences)
        if not isinstance(plan, RejectReason):
            plans.append((style, plan))
    return plans


def _group_identical(
    plans: Iterable[tuple[RouteStyle, MarchPlan]],
) -> list[tuple[list[RouteStyle], MarchPlan]]:
    groups: dict[tuple[tuple[RegionId, ...], bool], tuple[list[RouteStyle], MarchPlan]]
    groups = {}
    for style, plan in plans:
        key = (tuple(plan.route), plan.is_returning)
        styles, _ = groups.setdefault(key, ([], plan))
        styles.append(style)
    return list(groups.values())


def preview_routes(
    world: WorldState,
    scenario: StrategyScenario,
    army_id: ArmyId,
    to_region_id: RegionId,
    via: tuple[RegionId, ...] = (),
    avoid: frozenset[RegionId] = frozenset(),
) -> list[RoutePreview]:
    """Route options for an order, one per distinct route, in style order.

    Returns an empty list when no style can plan the order (unknown army or region,
    nothing reachable, destination avoided); the order itself reports the reason.
    """
    army = world.armies.get(army_id)
    if army is None:
        return []
    run = MovementRun(
        world=world,
        index=build_map_index(scenario.map),
        tuning=scenario.tuning.movement,
    )
    visible = visible_regions(world, army.owner_id, run.index)
    grouped = _group_identical(_plans_by_style(run, army, to_region_id, via, avoid))
    return [
        RoutePreview(
            styles=styles,
            route=plan.route,
            is_turning_back=plan.is_returning,
            base_cost=_base_cost(run, army, plan),
            estimated_turns=_estimated_turns(run, army, plan),
            warnings=_warnings(run, army, plan, visible),
        )
        for styles, plan in grouped
    ]
