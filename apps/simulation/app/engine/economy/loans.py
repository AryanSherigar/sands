from app.engine.economy import events
from app.engine.economy.arithmetic import PERCENT, ceil_division, percent_of
from app.engine.economy.credit import loan_interest_percent, register_default
from app.engine.economy.ledger import available_cash, change_treasury
from app.engine.economy.state import EconomyRun
from app.models.world_faction import FactionState, LoanState
from strategy_contracts.ids import FactionId


def interest_due(loan: LoanState) -> int:
    return ceil_division(loan.principal * loan.interest_percent, PERCENT)


def installment_due(loan: LoanState, installment_percent: int) -> int:
    return min(loan.principal, max(1, percent_of(loan.principal, installment_percent)))


def take_loan(
    run: EconomyRun, faction_id: FactionId, requested: int, granted: int, reason: str
) -> None:
    faction = run.world.factions[faction_id]
    interest_percent = loan_interest_percent(run.tuning, faction)
    faction.loans.append(
        LoanState(
            principal=granted,
            interest_percent=interest_percent,
            turns_remaining=run.tuning.loan_term_turns,
        )
    )
    run.fresh_loans.add((faction_id, len(faction.loans) - 1))
    change = change_treasury(faction, granted)
    run.events.append(
        events.loan_taken(
            faction_id, requested, granted, interest_percent, change, reason
        )
    )


def pay_interest(run: EconomyRun, faction_id: FactionId) -> int:
    faction = run.world.factions[faction_id]
    cash = available_cash(faction)
    due = paid = 0
    for index, loan in enumerate(faction.loans):
        if (faction_id, index) in run.fresh_loans:
            continue
        owed = interest_due(loan)
        payment = min(owed, cash - paid)
        loan.principal += owed - payment
        due += owed
        paid += payment
    if due:
        change = change_treasury(faction, -paid) if paid else None
        run.events.append(events.interest_paid(faction_id, due, paid, change))
    return paid


def _repay_loan(
    run: EconomyRun, faction: FactionState, loan: LoanState, surplus: int
) -> int:
    installment = installment_due(loan, run.tuning.loan_installment_percent)
    payment = min(installment, surplus, available_cash(faction))
    if payment == 0:
        return 0
    loan.principal -= payment
    change = change_treasury(faction, -payment)
    run.events.append(events.loan_repaid(faction.id, payment, loan.principal, change))
    return payment


def _age_loan(run: EconomyRun, faction: FactionState, loan: LoanState) -> None:
    loan.turns_remaining = max(0, loan.turns_remaining - 1)
    if loan.turns_remaining > 0:
        return
    surcharge = run.tuning.loan_strike_surcharge_percent
    loan.interest_percent = min(PERCENT, loan.interest_percent + surcharge)
    loan.turns_remaining = run.tuning.loan_term_turns
    run.events.append(
        events.loan_overdue(faction.id, loan.principal, loan.interest_percent)
    )
    register_default(run, faction.id)


def repay_loans(run: EconomyRun, faction_id: FactionId, surplus: int) -> None:
    faction = run.world.factions[faction_id]
    remaining = surplus
    for index, loan in enumerate(faction.loans):
        if (faction_id, index) in run.fresh_loans:
            continue
        remaining -= _repay_loan(run, faction, loan, remaining)
        if loan.principal > 0:
            _age_loan(run, faction, loan)
    faction.loans = [loan for loan in faction.loans if loan.principal > 0]
