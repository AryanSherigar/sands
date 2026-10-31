import pytest
from app.engine.negotiation import OfferReaction, acceptance_range, react_to_pact
from app.engine.peace.acceptance import does_counterpart_accept
from app.engine.treaty.ledger import CardVerdict, evaluate_card
from strategy_contracts.terms import (
    MilitaryAccessTerm,
    NonAggressionTerm,
    PayGoldTerm,
    TermsCard,
    TradeDealTerm,
)
from strategy_contracts.treaty import Verdict, WeightBand

from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_peace_card,
    make_world,
    set_score,
)

MAX_TURNS = SCENARIO.negotiation.max_pact_turns
REACTION_TO_VERDICT = {
    OfferReaction.ACCEPT: Verdict.ACCEPT,
    OfferReaction.HAGGLE: Verdict.HAGGLE,
    OfferReaction.REFUSE: Verdict.REFUSE,
}


def _card(rival_id: str, *terms) -> TermsCard:
    return TermsCard(
        proposer_id=PLAYER,
        counterpart_id=rival_id,
        terms=list(terms),
        is_confirmed_by_counterpart=True,
    )


def _pact(rival_id: str, turns: int) -> NonAggressionTerm:
    return NonAggressionTerm(faction_a=PLAYER, faction_b=rival_id, duration_turns=turns)


@pytest.mark.parametrize("rival_id", [WRATHFUL_RIVAL, CAUTIOUS_RIVAL])
@pytest.mark.parametrize("turns", range(1, MAX_TURNS + 3))
def test_pact_only_card_matches_the_legacy_reaction(rival_id: str, turns: int) -> None:
    world = make_world()
    limits = acceptance_range(world, SCENARIO, PLAYER, rival_id)

    result = evaluate_card(
        world, SCENARIO, _card(rival_id, _pact(rival_id, turns)), None
    )

    assert result.verdict is REACTION_TO_VERDICT[react_to_pact(limits, turns)]


@pytest.mark.parametrize(
    ("attacker_score", "defender_score"), [(0, 0), (30, 0), (60, 5)]
)
@pytest.mark.parametrize("tier", ["short", "medium", "perpetual"])
def test_peace_card_acceptance_matches_the_legacy_rule(
    attacker_score: int, defender_score: int, tier: str
) -> None:
    world = make_world()
    war = set_score(add_war(world), attacker_score, defender_score)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [], tier=tier)

    result = evaluate_card(world, SCENARIO, card, war)

    expected = does_counterpart_accept(world, SCENARIO, card, war)
    assert (result.verdict is Verdict.ACCEPT) is expected


def test_heavy_demand_with_nothing_offered_is_refused() -> None:
    world = make_world()
    demands = [
        PayGoldTerm(payer_id=WRATHFUL_RIVAL, payee_id=PLAYER, amount=1000)
        for _ in range(8)
    ]

    result = evaluate_card(world, SCENARIO, _card(WRATHFUL_RIVAL, *demands), None)

    assert result.verdict is Verdict.REFUSE


def test_a_trade_deal_lifts_a_pact_that_would_only_haggle() -> None:
    world = make_world()
    limits = acceptance_range(world, SCENARIO, PLAYER, WRATHFUL_RIVAL)
    turns = next(
        turn
        for turn in range(1, MAX_TURNS + 1)
        if react_to_pact(limits, turn) is OfferReaction.HAGGLE
    )
    trade = TradeDealTerm(
        faction_a=PLAYER, faction_b=WRATHFUL_RIVAL, duration_turns=MAX_TURNS
    )
    pact = _pact(WRATHFUL_RIVAL, turns)

    alone = evaluate_card(world, SCENARIO, _card(WRATHFUL_RIVAL, pact), None)
    combined = evaluate_card(world, SCENARIO, _card(WRATHFUL_RIVAL, pact, trade), None)

    assert (alone.verdict, combined.verdict) == (Verdict.HAGGLE, Verdict.ACCEPT)


def test_asking_for_passage_costs_more_than_granting_it() -> None:
    world = make_world()
    asking = MilitaryAccessTerm(
        grantor_id=WRATHFUL_RIVAL, grantee_id=PLAYER, duration_turns=MAX_TURNS
    )
    granting = MilitaryAccessTerm(
        grantor_id=PLAYER, grantee_id=WRATHFUL_RIVAL, duration_turns=MAX_TURNS
    )
    pact = _pact(WRATHFUL_RIVAL, MAX_TURNS)

    ask = evaluate_card(world, SCENARIO, _card(WRATHFUL_RIVAL, pact, asking), None)
    grant = evaluate_card(world, SCENARIO, _card(WRATHFUL_RIVAL, pact, granting), None)

    assert ask.verdict is not Verdict.ACCEPT
    assert grant.verdict is Verdict.ACCEPT


def test_bands_cover_every_clause_and_carry_no_numbers() -> None:
    world = make_world()
    card = _card(
        WRATHFUL_RIVAL,
        _pact(WRATHFUL_RIVAL, 4),
        TradeDealTerm(faction_a=PLAYER, faction_b=WRATHFUL_RIVAL, duration_turns=4),
    )

    result = evaluate_card(world, SCENARIO, card, None)

    assert isinstance(result, CardVerdict)
    assert len(result.bands) == len(card.terms)
    assert all(isinstance(band, WeightBand) for band in result.bands)
