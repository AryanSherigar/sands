from app.engine.negotiation import acceptance_range
from app.engine.peace.pricing import can_afford, price_card
from app.engine.pressure.wars import side_score
from app.models.world_diplomacy import WarState
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import TermsCard


def does_counterpart_accept(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard,
    war: WarState,
) -> bool:
    """Counterpart ends the war when the proposer's edge, plus what the proposer concedes, reaches its acceptance line."""
    proposer_id, counterpart_id = card.proposer_id, card.counterpart_id
    if not can_afford(world, scenario, card, proposer_id, war):
        return False
    concession = price_card(scenario, card, proposer_id).concession
    edge = side_score(war, proposer_id) - side_score(war, counterpart_id)
    limits = acceptance_range(world, scenario, proposer_id, counterpart_id)
    return edge + concession >= limits.accept_at
