from dataclasses import dataclass

from app.engine.ai.standing import FULL_PERCENT, known_power_ratio
from app.engine.negotiation import acceptance_range
from app.engine.peace.pricing import CardPrice, can_afford
from app.engine.pressure.wars import side_score
from app.engine.treaty.registry import price_clause
from app.models.world_diplomacy import WarState
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import TermsCard, VassalTerm
from strategy_contracts.treaty import Verdict, WeightBand

FREE = CardPrice(demand=0, concession=0)
REASON_UNAFFORDABLE = "unaffordable"
REASON_OUTSIDE_LIMITS = "outside_limits"
REASON_HAGGLE = "haggle"
LIGHT_QUARTERS = 1
MODERATE_QUARTERS = 3
QUARTERS = 4


@dataclass(frozen=True)
class CardVerdict:
    verdict: Verdict
    bands: tuple[WeightBand, ...]
    reason: str | None = None


def _band_of(weight: int, accept_at: int) -> WeightBand:
    scaled = abs(weight) * QUARTERS
    line = max(accept_at, 1)
    if scaled < line * LIGHT_QUARTERS:
        return WeightBand.LIGHT
    if scaled < line * MODERATE_QUARTERS:
        return WeightBand.MODERATE
    return WeightBand.HEAVY


def _vassal_leverage(
    world: WorldState, scenario: StrategyScenario, card: TermsCard
) -> int:
    if not any(isinstance(term, VassalTerm) for term in card.terms):
        return 0
    ratio = known_power_ratio(world, scenario, card.counterpart_id, card.proposer_id)
    return max(0, FULL_PERCENT - ratio)


def _card_value(
    prices: list[CardPrice], card: TermsCard, war: WarState | None, leverage: int
) -> int:
    concession = sum(price.concession for price in prices) + leverage
    if war is None:
        return concession - sum(price.demand for price in prices)
    proposer_id, counterpart_id = card.proposer_id, card.counterpart_id
    edge = side_score(war, proposer_id) - side_score(war, counterpart_id)
    return edge + concession


def _verdict_of(
    value: int, accept_at: int, haggle_at: int
) -> tuple[Verdict, str | None]:
    if value >= accept_at:
        return Verdict.ACCEPT, None
    if value >= haggle_at:
        return Verdict.HAGGLE, REASON_HAGGLE
    return Verdict.REFUSE, REASON_OUTSIDE_LIMITS


def evaluate_card(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard,
    war: WarState | None,
) -> CardVerdict:
    """Net value the counterpart weighs for the whole card against its hidden acceptance line."""
    proposer_id, counterpart_id = card.proposer_id, card.counterpart_id
    limits = acceptance_range(world, scenario, proposer_id, counterpart_id)
    prices = [price_clause(term, proposer_id, scenario) for term in card.terms]
    bands = tuple(
        _band_of(price.concession - price.demand, limits.accept_at) for price in prices
    )
    if war is not None and not can_afford(world, scenario, card, proposer_id, war):
        return CardVerdict(Verdict.REFUSE, bands, REASON_UNAFFORDABLE)
    if war is None and all(price == FREE for price in prices):
        return CardVerdict(Verdict.ACCEPT, bands)
    leverage = _vassal_leverage(world, scenario, card)
    value = _card_value(prices, card, war, leverage)
    verdict, reason = _verdict_of(value, limits.accept_at, limits.haggle_at)
    return CardVerdict(verdict, bands, reason)
