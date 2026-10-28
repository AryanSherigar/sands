from collections.abc import Callable, Sequence

from app.engine.economy import events
from app.engine.economy.arithmetic import ceil_division
from app.engine.economy.armies import next_army_id, remove_army
from app.engine.economy.credit import available_credit
from app.engine.economy.ledger import available_cash, change_treasury
from app.engine.economy.loans import take_loan
from app.engine.economy.manpower import manpower_room
from app.engine.economy.reasons import RejectReason
from app.engine.economy.state import EconomyRun
from app.models.orders import (
    DeclareDefaultOrder,
    DisbandArmyOrder,
    QueuedOrder,
    RaiseArmyOrder,
    SetPayOrder,
    SetTaxRateOrder,
    TakeLoanOrder,
)
from app.models.world_army import ArmyState
from app.models.world_events import StateChange
from app.models.world_state import WorldState
from strategy_contracts.enums import TroopType
from strategy_contracts.ids import ArmyId, FactionId

ECONOMY_ORDER_TYPES = (
    SetTaxRateOrder,
    SetPayOrder,
    TakeLoanOrder,
    DeclareDefaultOrder,
    RaiseArmyOrder,
    DisbandArmyOrder,
)
ORDER_SUMMARY_LOAN = "order_take_loan"


def _faction_problem(world: WorldState, faction_id: FactionId) -> RejectReason | None:
    faction = world.factions.get(faction_id)
    if faction is None:
        return RejectReason.UNKNOWN_FACTION
    if faction.is_destroyed:
        return RejectReason.FACTION_DESTROYED
    return None


def _army_problem(
    run: EconomyRun,
    army_id: ArmyId,
    faction_id: FactionId,
    can_be_engaged: bool = False,
) -> RejectReason | None:
    army = run.world.armies.get(army_id)
    if army is None:
        return RejectReason.UNKNOWN_ARMY
    if army.owner_id != faction_id:
        return RejectReason.NOT_YOUR_ARMY
    if army_id in run.battle_army_ids and not can_be_engaged:
        return RejectReason.IN_BATTLE
    return None


def _reject(run: EconomyRun, subject_id: str, reason: RejectReason) -> None:
    run.events.append(events.order_rejected(subject_id, reason.value))


def _apply_tax_rate(run: EconomyRun, order: SetTaxRateOrder) -> None:
    faction = run.world.factions[order.faction_id]
    if faction.tax_rate is order.tax_rate:
        return
    before = faction.tax_rate.value
    faction.tax_rate = order.tax_rate
    run.events.append(events.tax_rate_set(faction.id, before, order.tax_rate.value))


def _apply_pay(run: EconomyRun, order: SetPayOrder) -> None:
    problem = _army_problem(run, order.army_id, order.faction_id, run.can_pay_engaged)
    if problem is not None:
        _reject(run, order.army_id, problem)
        return
    army = run.world.armies[order.army_id]
    if army.pay_level is order.pay_level:
        return
    before = army.pay_level.value
    army.pay_level = order.pay_level
    run.events.append(events.pay_set(army.id, before, order.pay_level.value))


def _loan_problem(run: EconomyRun, order: TakeLoanOrder) -> RejectReason | None:
    if not run.is_loans_enabled:
        return RejectReason.LOANS_DISABLED
    if order.amount <= 0:
        return RejectReason.INVALID_AMOUNT
    if available_credit(run.world, run.tuning, order.faction_id) == 0:
        return RejectReason.NO_CREDIT
    return None


def _apply_loan(run: EconomyRun, order: TakeLoanOrder) -> None:
    problem = _loan_problem(run, order)
    if problem is not None:
        _reject(run, order.faction_id, problem)
        return
    credit = available_credit(run.world, run.tuning, order.faction_id)
    granted = min(order.amount, credit)
    take_loan(run, order.faction_id, order.amount, granted, ORDER_SUMMARY_LOAN)


def _apply_declare_default(run: EconomyRun, order: DeclareDefaultOrder) -> None:
    run.declared_defaults.add(order.faction_id)
    run.events.append(events.default_declared(order.faction_id))


def _recruit_cost(run: EconomyRun, troops: dict[TroopType, int]) -> int:
    raw = sum(
        count * run.tuning.recruit_cost_per_unit[troop_type]
        for troop_type, count in troops.items()
    )
    return ceil_division(raw, run.tuning.upkeep_troop_unit)


def _levy_problem(run: EconomyRun, order: RaiseArmyOrder) -> RejectReason | None:
    region = run.world.regions.get(order.region_id)
    if region is None:
        return RejectReason.UNKNOWN_REGION
    if region.owner_id != order.faction_id:
        return RejectReason.NOT_YOUR_REGION
    if region.occupation is not None:
        return RejectReason.REGION_OCCUPIED
    if sum(order.troops.values()) == 0:
        return RejectReason.EMPTY_LEVY
    if sum(order.troops.values()) > region.manpower:
        return RejectReason.INSUFFICIENT_MANPOWER
    if _recruit_cost(run, order.troops) > available_cash(
        run.world.factions[order.faction_id]
    ):
        return RejectReason.INSUFFICIENT_FUNDS
    return None


def _new_army(run: EconomyRun, order: RaiseArmyOrder) -> ArmyState:
    return ArmyState(
        id=next_army_id(run.world),
        owner_id=order.faction_id,
        troops={kind: count for kind, count in order.troops.items() if count > 0},
        morale=run.tuning.raised_army_morale,
        location_id=order.region_id,
    )


def _apply_raise(run: EconomyRun, order: RaiseArmyOrder) -> None:
    problem = _levy_problem(run, order)
    if problem is not None:
        _reject(run, order.region_id, problem)
        return
    region = run.world.regions[order.region_id]
    army = _new_army(run, order)
    levy = sum(army.troops.values())
    cost = _recruit_cost(run, army.troops)
    changes = [
        StateChange(
            path=f"regions.{region.id}.manpower",
            before=region.manpower,
            after=region.manpower - levy,
        ),
        change_treasury(run.world.factions[order.faction_id], -cost),
    ]
    region.manpower -= levy
    run.world.armies[army.id] = army
    troops = {kind.value: count for kind, count in army.troops.items()}
    run.events.append(
        events.army_raised(order.faction_id, army.id, region.id, troops, cost, changes)
    )


def _return_manpower(run: EconomyRun, army: ArmyState) -> list[StateChange]:
    region = run.world.regions[army.location_id]
    if region.owner_id != army.owner_id:
        return []
    wanted = sum(army.troops.values()) * run.tuning.disband_return_percent // 100
    returned = min(wanted, manpower_room(region, run.tuning))
    change = StateChange(
        path=f"regions.{region.id}.manpower",
        before=region.manpower,
        after=region.manpower + returned,
    )
    region.manpower += returned
    return [change]


def _apply_disband(run: EconomyRun, order: DisbandArmyOrder) -> None:
    problem = _army_problem(run, order.army_id, order.faction_id)
    if problem is not None:
        _reject(run, order.army_id, problem)
        return
    army = run.world.armies[order.army_id]
    changes = _return_manpower(run, army)
    returned = changes[0].after - changes[0].before if changes else 0
    remove_army(run.world, army.id)
    run.events.append(events.army_disbanded(army.owner_id, army.id, returned, changes))


HANDLERS: dict[type, Callable[[EconomyRun, object], None]] = {
    SetTaxRateOrder: _apply_tax_rate,
    SetPayOrder: _apply_pay,
    TakeLoanOrder: _apply_loan,
    DeclareDefaultOrder: _apply_declare_default,
    RaiseArmyOrder: _apply_raise,
    DisbandArmyOrder: _apply_disband,
}


def economy_orders(orders: Sequence[QueuedOrder]) -> list[QueuedOrder]:
    return sorted(
        (queued for queued in orders if isinstance(queued.order, ECONOMY_ORDER_TYPES)),
        key=lambda queued: queued.id,
    )


def apply_economy_orders(run: EconomyRun, orders: Sequence[QueuedOrder]) -> None:
    for queued in economy_orders(orders):
        order = queued.order
        problem = _faction_problem(run.world, order.faction_id)
        if problem is not None:
            _reject(run, order.faction_id, problem)
            continue
        HANDLERS[type(order)](run, order)
