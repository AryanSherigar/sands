from collections.abc import Sequence
from dataclasses import dataclass

from app.engine.economy.credit import available_credit
from app.engine.economy.income import faction_income
from app.engine.economy.loans import interest_due
from app.engine.economy.orders import apply_economy_orders
from app.engine.economy.state import start_run
from app.engine.economy.upkeep import faction_upkeep
from app.exceptions.world_exceptions import UnknownFactionError
from app.models.orders import QueuedOrder
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


@dataclass(frozen=True)
class BalanceProjection:
    income: int
    interest: int
    upkeep: int
    balance_after: int
    shortfall: int
    available_credit: int
    is_default_declared: bool

    @property
    def is_unresolved(self) -> bool:
        return self.shortfall > 0 and not self.is_default_declared


def project_balance(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    queued_orders: Sequence[QueuedOrder],
) -> BalanceProjection:
    if faction_id not in world.factions:
        raise UnknownFactionError(faction_id)
    run = start_run(world.model_copy(deep=True), scenario)
    apply_economy_orders(run, queued_orders)
    faction = run.world.factions[faction_id]
    income = faction_income(run.world, run.tuning, faction_id).total
    cash = max(0, faction.treasury + income)
    interest_owed = sum(
        interest_due(loan)
        for index, loan in enumerate(faction.loans)
        if (faction_id, index) not in run.fresh_loans
    )
    interest = min(interest_owed, cash)
    upkeep = sum(faction_upkeep(run.world, run.tuning, faction_id).values())
    balance_after = cash - interest - upkeep
    return BalanceProjection(
        income=income,
        interest=interest,
        upkeep=upkeep,
        balance_after=balance_after,
        shortfall=max(0, -balance_after),
        available_credit=available_credit(run.world, run.tuning, faction_id),
        is_default_declared=faction_id in run.declared_defaults,
    )
