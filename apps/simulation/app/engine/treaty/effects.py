from app.engine.diplomacy.events import diplomacy_event
from app.engine.economy.income import faction_income
from app.engine.economy.ledger import available_cash, change_treasury
from app.engine.economy.state import EconomyRun
from app.engine.proclamations.constants import MODIFIER_TRADE_EFFICIENCY
from app.engine.proclamations.modifiers import active_modifier
from app.engine.treaty.standing import is_in_force
from app.engine.vassals.tribute import TRIBUTE_PAID
from app.models.world_diplomacy import CommitmentState
from app.models.world_events import PhaseName
from app.models.world_state import WorldState
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.terms import TradeDealTerm, TributeTerm

TRADE_INCOME = "trade_income"


def _in_force(world: WorldState, term_type: type) -> list[CommitmentState]:
    return sorted(
        (
            item
            for item in world.commitments
            if isinstance(item.term, term_type) and is_in_force(world, item)
        ),
        key=lambda item: item.id,
    )


def _collect_trade(run: EconomyRun) -> None:
    world = run.world
    percent = run.treaty_tuning.trade_income_percent
    for commitment in _in_force(world, TradeDealTerm):
        term = commitment.term
        assert isinstance(term, TradeDealTerm)
        changes = []
        for faction_id in (term.faction_a, term.faction_b):
            income = faction_income(world, run.tuning, faction_id).total
            gain = income * percent // FULL_SHARE_PERCENT
            efficiency = active_modifier(world, faction_id, MODIFIER_TRADE_EFFICIENCY)
            gain = max(
                0, gain * (FULL_SHARE_PERCENT + efficiency) // FULL_SHARE_PERCENT
            )
            changes.append(change_treasury(world.factions[faction_id], gain))
        run.events.append(
            diplomacy_event(
                TRADE_INCOME,
                [term.faction_a, term.faction_b],
                phase=PhaseName.ECONOMY,
                changes=changes,
            )
        )


def _collect_tribute(run: EconomyRun) -> None:
    world = run.world
    for commitment in _in_force(world, TributeTerm):
        term = commitment.term
        assert isinstance(term, TributeTerm)
        payer = world.factions[term.payer_id]
        amount = min(term.gold_per_turn, available_cash(payer))
        if amount <= 0:
            continue
        changes = [
            change_treasury(payer, -amount),
            change_treasury(world.factions[term.payee_id], amount),
        ]
        run.events.append(
            diplomacy_event(
                TRIBUTE_PAID,
                [term.payee_id, term.payer_id],
                {"amount": amount},
                phase=PhaseName.ECONOMY,
                changes=changes,
            )
        )


def collect_trade_and_tribute(run: EconomyRun) -> None:
    if run.world.treaty_ruleset < 1:
        return
    _collect_trade(run)
    _collect_tribute(run)
