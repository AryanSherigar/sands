from app.engine.ai.candidates import Candidate
from app.engine.ai.situation import is_hostile
from app.engine.economy.credit import available_credit
from app.models.orders import DisbandArmyOrder, SetPayOrder, TakeLoanOrder
from app.models.world_army import ArmyState
from app.models.world_state import WorldState
from strategy_contracts.enums import PayLevel
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory

RICH_TREASURY_MULTIPLE = 2


def _own_armies(world: WorldState, faction_id: FactionId) -> list[ArmyState]:
    return [
        army for _, army in sorted(world.armies.items()) if army.owner_id == faction_id
    ]


def loan_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    if not scenario.toggles.is_loans_enabled:
        return []
    if world.factions[faction_id].treasury >= tuning.low_treasury:
        return []
    owed = sum(loan.principal for loan in world.factions[faction_id].loans)
    if owed >= tuning.loan_cap:
        return []
    credit = available_credit(world, scenario.tuning.economy, faction_id)
    amount = min(credit, tuning.loan_cap)
    if amount <= 0:
        return []
    order = TakeLoanOrder(faction_id=faction_id, amount=amount)
    return [Candidate(order, ScoreCategory.HOARD, tuning.situation_bonus)]


def pay_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    treasury = world.factions[faction_id].treasury
    is_poor = treasury < tuning.low_treasury
    is_rich = treasury >= tuning.low_treasury * RICH_TREASURY_MULTIPLE
    candidates: list[Candidate] = []
    for army in _own_armies(world, faction_id):
        if is_poor and army.pay_level == PayLevel.FULL:
            order = SetPayOrder(
                faction_id=faction_id, army_id=army.id, pay_level=PayLevel.REDUCED
            )
            candidates.append(Candidate(order, ScoreCategory.HOARD))
        if is_rich and army.pay_level == PayLevel.REDUCED:
            order = SetPayOrder(
                faction_id=faction_id, army_id=army.id, pay_level=PayLevel.FULL
            )
            candidates.append(Candidate(order, ScoreCategory.BUILD))
    return candidates


def disband_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    if world.factions[faction_id].treasury >= tuning.low_treasury:
        return []
    if is_hostile(world, faction_id):
        return []
    return [
        Candidate(
            DisbandArmyOrder(faction_id=faction_id, army_id=army.id),
            ScoreCategory.HOARD,
        )
        for army in _own_armies(world, faction_id)
        if sum(army.troops.values()) <= tuning.disband_below_troops
    ]
