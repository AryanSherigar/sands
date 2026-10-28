from app.engine.ai.standing import FULL_PERCENT, known_power_ratio
from app.engine.negotiation import acceptance_range
from app.engine.vassals.pricing import vassal_price
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import VassalTerm


def does_counterpart_accept_vassalage(
    world: WorldState,
    scenario: StrategyScenario,
    term: VassalTerm,
    proposer_id: FactionId,
) -> bool:
    """The burden must fit inside the leverage the weaker side concedes, on top of its acceptance line."""
    counterpart_id = (
        term.vassal_id if term.overlord_id == proposer_id else term.overlord_id
    )
    leverage = max(
        0,
        FULL_PERCENT - known_power_ratio(world, scenario, counterpart_id, proposer_id),
    )
    limits = acceptance_range(world, scenario, proposer_id, counterpart_id)
    return leverage >= limits.accept_at + vassal_price(term, scenario.tuning.vassal)
