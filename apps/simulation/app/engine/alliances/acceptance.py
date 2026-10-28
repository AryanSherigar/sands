from app.engine.alliances.pricing import alliance_price
from app.engine.negotiation import acceptance_range
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import AllianceTerm


def does_counterpart_accept_alliance(
    world: WorldState,
    scenario: StrategyScenario,
    term: AllianceTerm,
    proposer_id: FactionId,
) -> bool:
    counterpart_id = term.faction_b if term.faction_a == proposer_id else term.faction_a
    limits = acceptance_range(world, scenario, proposer_id, counterpart_id)
    return alliance_price(term, scenario.tuning.alliance) >= limits.accept_at
