from collections.abc import Sequence

from app.engine.movement import events
from app.engine.movement.attack import attack_problem
from app.engine.movement.engagement import armies_in_open_battle
from app.engine.movement.reasons import RejectReason
from app.engine.movement.route_options import RoutePreferences
from app.engine.movement.route_planning import MarchPlan, plan_march
from app.engine.movement.state import MovementRun
from app.models.orders import AttackOrder, HaltArmyOrder, MoveArmyOrder, QueuedOrder
from app.models.world_army import ArmyOrderState, ArmyState, MarchState
from app.models.world_character import CommanderStatus
from strategy_contracts.enums import OrderKind
from strategy_contracts.ids import ArmyId, RegionId


def _ownership_problem(
    run: MovementRun, army_id: ArmyId, faction_id: str
) -> RejectReason | None:
    army = run.world.armies.get(army_id)
    faction = run.world.factions.get(faction_id)
    if army is None:
        return RejectReason.UNKNOWN_ARMY
    if faction is None or army.owner_id != faction_id:
        return RejectReason.NOT_YOUR_ARMY
    if faction.is_destroyed:
        return RejectReason.FACTION_DESTROYED
    return None


def _readiness_problem(run: MovementRun, army: ArmyState) -> RejectReason | None:
    if sum(army.troops.values()) == 0:
        return RejectReason.EMPTY_ARMY
    commander = run.world.commanders.get(army.commander_id or "")
    if commander is not None and commander.status is not CommanderStatus.ACTIVE:
        return RejectReason.COMMANDER_UNAVAILABLE
    if army.id in armies_in_open_battle(run.world):
        return RejectReason.IN_BATTLE
    return None


def _start_march(army: ArmyState, plan: MarchPlan, destination: RegionId) -> None:
    previous = army.march
    carried = previous.leg_progress if previous is not None else 0
    if plan.is_returning and previous is not None:
        army.march = MarchState(
            from_id=army.location_id,
            to_id=previous.to_id,
            route=plan.route,
            leg_progress=carried,
            is_returning=True,
        )
    else:
        army.march = MarchState(
            from_id=army.location_id,
            to_id=plan.route[0],
            route=plan.route[1:],
            leg_progress=carried,
        )
    army.order = ArmyOrderState(kind=OrderKind.MOVE_ARMY, target_id=destination)


def _preferences_of(order: MoveArmyOrder) -> RoutePreferences:
    return RoutePreferences(
        style=order.route_style,
        via=tuple(order.via_region_ids),
        avoid=frozenset(order.avoid_region_ids),
    )


def _apply_move(run: MovementRun, order: MoveArmyOrder) -> None:
    army = run.world.armies[order.army_id]
    problem = _readiness_problem(run, army)
    outcome = problem or plan_march(
        run, army, order.to_region_id, _preferences_of(order)
    )
    if isinstance(outcome, RejectReason):
        run.events.append(events.order_rejected(army.id, outcome.value))
        return
    progress = army.march.leg_progress if army.march else 0
    _start_march(army, outcome, order.to_region_id)
    run.events.append(_start_event(army.id, outcome, progress))


def _apply_attack(run: MovementRun, order: AttackOrder) -> None:
    army = run.world.armies[order.army_id]
    problem = attack_problem(run, army, order.target_region_id)
    if problem is not None:
        run.events.append(events.order_rejected(army.id, problem.value))
        return
    march = MoveArmyOrder(
        faction_id=order.faction_id,
        army_id=order.army_id,
        to_region_id=order.target_region_id,
    )
    _apply_move(run, march)


def _start_event(army_id: ArmyId, plan: MarchPlan, progress: int):
    if plan.is_returning:
        return events.army_turned_back(army_id, progress)
    return events.march_started(army_id, len(plan.route))


def _apply_halt(run: MovementRun, order: HaltArmyOrder) -> None:
    army = run.world.armies[order.army_id]
    if army.march is None:
        return
    progress = army.march.leg_progress
    if progress > 0:
        army.march = MarchState(
            from_id=army.march.from_id,
            to_id=army.march.to_id,
            leg_progress=progress,
            is_halted=True,
        )
    else:
        army.march = None
    army.order = None
    run.events.append(events.army_halted(army.id, progress))


def _movement_orders(orders: Sequence[QueuedOrder]) -> list[QueuedOrder]:
    return sorted(
        (
            queued
            for queued in orders
            if isinstance(queued.order, MoveArmyOrder | AttackOrder | HaltArmyOrder)
        ),
        key=lambda queued: queued.id,
    )


def apply_orders(run: MovementRun, orders: Sequence[QueuedOrder]) -> None:
    handled: set[ArmyId] = set()
    for queued in _movement_orders(orders):
        order = queued.order
        problem = _ownership_problem(run, order.army_id, order.faction_id)
        if problem is None and order.army_id in handled:
            problem = RejectReason.DUPLICATE_ORDER
        if problem is not None:
            run.events.append(events.order_rejected(order.army_id, problem.value))
            continue
        handled.add(order.army_id)
        if isinstance(order, MoveArmyOrder):
            _apply_move(run, order)
        elif isinstance(order, AttackOrder):
            _apply_attack(run, order)
        else:
            _apply_halt(run, order)
