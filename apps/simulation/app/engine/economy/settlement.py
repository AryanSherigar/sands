from app.engine.economy import events
from app.engine.economy.credit import recover_credit, register_default
from app.engine.economy.income import collect_income
from app.engine.economy.ledger import available_cash, change_treasury
from app.engine.economy.loans import pay_interest, repay_loans
from app.engine.economy.manpower import refill_manpower
from app.engine.economy.pay_outcomes import apply_paid, apply_unpaid
from app.engine.economy.shortfall import apply_shortfall_decision, decide_shortfall
from app.engine.economy.state import EconomyRun
from app.engine.economy.unrest_drift import drift_unrest
from app.engine.economy.upkeep import faction_upkeep
from app.engine.phases import PhaseContext, ScenePause
from strategy_contracts.ids import ArmyId, FactionId


def _split_by_cash(
    cash: int, costs: dict[ArmyId, int]
) -> tuple[list[ArmyId], list[ArmyId]]:
    paid: list[ArmyId] = []
    unpaid: list[ArmyId] = []
    for army_id, cost in costs.items():
        if cost <= cash:
            cash -= cost
            paid.append(army_id)
        else:
            unpaid.append(army_id)
    return paid, unpaid


def _cover_shortfall(
    run: EconomyRun,
    faction_id: FactionId,
    costs: dict[ArmyId, int],
    context: PhaseContext,
) -> ScenePause | None:
    cash = available_cash(run.world.factions[faction_id])
    shortfall = sum(costs.values()) - cash
    if shortfall <= 0:
        return None
    decision = decide_shortfall(run, faction_id, context)
    if isinstance(decision, ScenePause):
        return decision
    apply_shortfall_decision(run, faction_id, shortfall, decision)
    return None


def _pay_armies(
    run: EconomyRun, faction_id: FactionId, costs: dict[ArmyId, int]
) -> int:
    if not costs:
        return 0
    faction = run.world.factions[faction_id]
    paid_ids, unpaid_ids = _split_by_cash(available_cash(faction), costs)
    paid_total = sum(costs[army_id] for army_id in paid_ids)
    change = change_treasury(faction, -paid_total)
    run.events.append(events.upkeep_paid(faction_id, costs, unpaid_ids, change))
    for army_id in paid_ids:
        apply_paid(run, run.world.armies[army_id])
    for army_id in unpaid_ids:
        apply_unpaid(run, run.world.armies[army_id])
    if unpaid_ids:
        register_default(run, faction_id)
    return paid_total


def settle_faction(
    run: EconomyRun, faction_id: FactionId, context: PhaseContext
) -> ScenePause | None:
    income = collect_income(run, faction_id)
    drift_unrest(run, faction_id)
    refill_manpower(run, faction_id)
    interest = pay_interest(run, faction_id)
    costs = faction_upkeep(run.world, run.tuning, faction_id)
    pause = _cover_shortfall(run, faction_id, costs, context)
    if pause is not None:
        return pause
    upkeep = _pay_armies(run, faction_id, costs)
    repay_loans(run, faction_id, max(0, income.total - interest - upkeep))
    recover_credit(run, faction_id)
    return None
