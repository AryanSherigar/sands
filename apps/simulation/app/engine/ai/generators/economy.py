from app.engine.ai.candidates import Candidate
from app.models.orders import SetTaxRateOrder
from app.models.world_state import WorldState
from strategy_contracts.enums import TaxRate
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory

TAX_CATEGORY: dict[TaxRate, ScoreCategory] = {
    TaxRate.HIGH: ScoreCategory.HOARD,
    TaxRate.NORMAL: ScoreCategory.BUILD,
    TaxRate.LOW: ScoreCategory.BUILD,
}

TAX_CHANGE_PENALTY = 4


def tax_rate_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    current = world.factions[faction_id].tax_rate
    return [
        Candidate(
            order=SetTaxRateOrder(faction_id=faction_id, tax_rate=rate),
            category=TAX_CATEGORY[rate],
            base_score=-TAX_CHANGE_PENALTY,
        )
        for rate in TaxRate
        if rate != current
    ]
