from dataclasses import dataclass

from app.engine.pressure.shocks import shock_total
from app.engine.pressure.wars import side_score
from app.engine.pressure.will import compute_will
from app.models.world_diplomacy import WarState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.peace import PeaceTuning
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import (
    CedeRegionTerm,
    HostageTerm,
    PayGoldTerm,
    PeaceTerm,
    ReleasePrisonersTerm,
    Term,
    TermsCard,
    TributeTerm,
)


@dataclass(frozen=True)
class CardPrice:
    demand: int
    concession: int


def _gold_to_score(gold: int, tuning: PeaceTuning) -> int:
    return gold // tuning.gold_per_score_point


def _price_cession(
    term: CedeRegionTerm, signer_id: FactionId, tuning: PeaceTuning
) -> CardPrice:
    cost = tuning.cede_region_score_cost
    if term.to_faction_id == signer_id:
        return CardPrice(demand=cost, concession=0)
    return CardPrice(demand=0, concession=cost)


def _price_payment(
    payer_id: FactionId, gold: int, signer_id: FactionId, tuning: PeaceTuning
) -> CardPrice:
    score = _gold_to_score(gold, tuning)
    if payer_id == signer_id:
        return CardPrice(demand=0, concession=score)
    return CardPrice(demand=score, concession=0)


def _price_flat(giver_id: FactionId, score: int, signer_id: FactionId) -> CardPrice:
    if giver_id == signer_id:
        return CardPrice(demand=0, concession=score)
    return CardPrice(demand=score, concession=0)


def price_term(term: Term, signer_id: FactionId, tuning: PeaceTuning) -> CardPrice:
    if isinstance(term, PeaceTerm):
        return CardPrice(demand=tuning.tier_score_cost[term.tier], concession=0)
    if isinstance(term, CedeRegionTerm):
        return _price_cession(term, signer_id, tuning)
    if isinstance(term, PayGoldTerm):
        return _price_payment(term.payer_id, term.amount, signer_id, tuning)
    if isinstance(term, TributeTerm):
        total = term.gold_per_turn * term.duration_turns
        return _price_payment(term.payer_id, total, signer_id, tuning)
    if isinstance(term, HostageTerm):
        return _price_flat(term.giver_id, tuning.hostage_score_value, signer_id)
    if isinstance(term, ReleasePrisonersTerm):
        score = tuning.prisoner_score_value * len(term.prisoner_ids)
        return _price_flat(term.holder_id, score, signer_id)
    return CardPrice(demand=0, concession=0)


def price_card(
    scenario: StrategyScenario, card: TermsCard, signer_id: FactionId
) -> CardPrice:
    tuning = scenario.tuning.peace
    prices = [price_term(term, signer_id, tuning) for term in card.terms]
    return CardPrice(
        demand=sum(price.demand for price in prices),
        concession=sum(price.concession for price in prices),
    )


def is_will_broken(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> bool:
    if shock_total(world, scenario, faction_id) == 0:
        return False
    will = compute_will(world, scenario, faction_id).value
    return will <= scenario.tuning.peace.broken_will_ceiling


def _other_side(war: WarState, faction_id: FactionId) -> FactionId:
    return war.defender_id if faction_id == war.attacker_id else war.attacker_id


def can_afford(
    world: WorldState,
    scenario: StrategyScenario,
    card: TermsCard,
    signer_id: FactionId,
    war: WarState,
) -> bool:
    demand = price_card(scenario, card, signer_id).demand
    if demand <= side_score(war, signer_id):
        return True
    return is_will_broken(world, scenario, _other_side(war, signer_id))
