from collections.abc import Callable

from app.engine.alliances.pricing import alliance_price
from app.engine.peace.pricing import (
    CardPrice,
    is_curved_release,
    price_release,
    price_term,
)
from app.engine.vassals.pricing import vassal_price
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import (
    AllianceTerm,
    ConditionalMode,
    ConditionalTerm,
    MilitaryAccessTerm,
    NonAggressionTerm,
    SwornPromiseTerm,
    Term,
    TradeDealTerm,
    VassalTerm,
    term_party_ids,
)

ClausePricer = Callable[[Term, FactionId, StrategyScenario], CardPrice]


def _offered(value: int) -> CardPrice:
    return CardPrice(demand=0, concession=value)


def _price_pact(
    term: NonAggressionTerm, signer_id: FactionId, scenario: StrategyScenario
) -> CardPrice:
    rules = scenario.negotiation
    turns = min(term.duration_turns, rules.max_pact_turns)
    return _offered(turns * rules.pact_value_per_turn)


def _price_trade(
    term: TradeDealTerm, signer_id: FactionId, scenario: StrategyScenario
) -> CardPrice:
    turns = min(term.duration_turns, scenario.negotiation.max_pact_turns)
    return _offered(turns * scenario.tuning.treaty.trade_value_per_turn)


def _price_access(
    term: MilitaryAccessTerm, signer_id: FactionId, scenario: StrategyScenario
) -> CardPrice:
    turns = min(term.duration_turns, scenario.negotiation.max_pact_turns)
    value = turns * scenario.tuning.treaty.access_value_per_turn
    if term.grantor_id == signer_id:
        return _offered(value)
    return CardPrice(demand=value, concession=0)


def _price_alliance(
    term: AllianceTerm, signer_id: FactionId, scenario: StrategyScenario
) -> CardPrice:
    return _offered(alliance_price(term, scenario.tuning.alliance))


def _price_vassal(
    term: VassalTerm, signer_id: FactionId, scenario: StrategyScenario
) -> CardPrice:
    price = vassal_price(term, scenario.tuning.vassal)
    return CardPrice(demand=price, concession=0)


def _price_promise(
    term: SwornPromiseTerm, signer_id: FactionId, scenario: StrategyScenario
) -> CardPrice:
    return CardPrice(demand=0, concession=0)


def _price_conditional(
    term: ConditionalTerm, signer_id: FactionId, scenario: StrategyScenario
) -> CardPrice:
    tuning = scenario.tuning.treaty
    percent = tuning.conditional_gate_percent
    if term.mode is ConditionalMode.TRIGGER:
        percent = tuning.conditional_trigger_percent
    inner = price_clause(term.inner, signer_id, scenario)
    return CardPrice(
        demand=inner.demand * percent // FULL_SHARE_PERCENT,
        concession=inner.concession * percent // FULL_SHARE_PERCENT,
    )


CLAUSE_PRICERS: dict[type[Term], ClausePricer] = {
    NonAggressionTerm: _price_pact,
    TradeDealTerm: _price_trade,
    MilitaryAccessTerm: _price_access,
    AllianceTerm: _price_alliance,
    VassalTerm: _price_vassal,
    SwornPromiseTerm: _price_promise,
    ConditionalTerm: _price_conditional,
}


def price_clause(
    term: Term,
    signer_id: FactionId,
    scenario: StrategyScenario,
    world: WorldState | None = None,
) -> CardPrice:
    if world is not None and is_curved_release(world, term):
        return price_release(world, scenario, term, signer_id)
    pricer = CLAUSE_PRICERS.get(type(term))
    if pricer is not None:
        return pricer(term, signer_id, scenario)
    return price_term(term, signer_id, scenario.tuning.peace)


def term_parties(term: Term) -> frozenset[FactionId]:
    if isinstance(term, ConditionalTerm):
        return term_party_ids(term.inner)
    return term_party_ids(term)
