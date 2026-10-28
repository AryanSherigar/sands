from app.engine.economy import events
from app.engine.economy.arithmetic import PERCENT, clamp
from app.engine.economy.income import faction_income
from app.engine.economy.state import EconomyRun
from app.models.world_events import StateChange
from app.models.world_faction import FactionState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import EconomyTuning


def total_principal(faction: FactionState) -> int:
    return sum(loan.principal for loan in faction.loans)


def loan_interest_percent(tuning: EconomyTuning, faction: FactionState) -> int:
    surcharge = faction.credit_strikes * tuning.loan_strike_surcharge_percent
    return min(PERCENT, tuning.loan_base_interest_percent + surcharge)


def available_credit(
    world: WorldState, tuning: EconomyTuning, faction_id: FactionId
) -> int:
    faction = world.factions[faction_id]
    if faction.credit_strikes >= tuning.loan_refused_strikes:
        return 0
    income = faction_income(world, tuning, faction_id).total
    limit = income * tuning.loan_cap_income_turns // (faction.credit_strikes + 1)
    return max(0, limit - total_principal(faction))


def register_default(run: EconomyRun, faction_id: FactionId) -> None:
    if faction_id in run.defaulted_factions:
        return
    run.defaulted_factions.add(faction_id)
    faction = run.world.factions[faction_id]
    before = faction.reputation
    faction.reputation = clamp(
        before - run.tuning.default_reputation_penalty, -PERCENT, PERCENT
    )
    faction.credit_strikes += 1
    faction.turns_since_default = 0
    change = StateChange(
        path=f"factions.{faction_id}.reputation",
        before=before,
        after=faction.reputation,
    )
    run.events.append(
        events.faction_defaulted(faction_id, faction.credit_strikes, change)
    )


def recover_credit(run: EconomyRun, faction_id: FactionId) -> None:
    faction = run.world.factions[faction_id]
    if faction_id in run.defaulted_factions or faction.credit_strikes == 0:
        return
    faction.turns_since_default += 1
    if faction.turns_since_default < run.tuning.credit_recovery_turns:
        return
    faction.credit_strikes -= 1
    faction.turns_since_default = 0
    run.events.append(events.credit_recovered(faction_id, faction.credit_strikes))
