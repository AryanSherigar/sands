from uuid import uuid4

import pytest
from app.engine.alliances.acceptance import does_counterpart_accept_alliance
from app.engine.negotiation import apply_terms_card
from app.engine.treaty.ledger import evaluate_card
from app.engine.vassals.acceptance import does_counterpart_accept_vassalage
from app.engine.vassals.registry import vassalage_of
from app.exceptions.command_exceptions import CampaignProgressError
from strategy_contracts.terms import (
    NonAggressionTerm,
    PromiseKind,
    SwornPromiseTerm,
    TermsCard,
    TradeDealTerm,
)
from strategy_contracts.treaty import Verdict

from tests.engine.alliances.builders import make_alliance_term
from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)
from tests.engine.vassals.builders import make_vassal_term

TURNS = 6


def _world(rival: str = WRATHFUL_RIVAL):
    world = make_world()
    world.treaty_ruleset = 1
    world.alliance_ruleset = 1
    world.vassal_ruleset = 1
    return world


def _card(rival: str, *terms) -> TermsCard:
    return TermsCard(
        proposer_id=PLAYER,
        counterpart_id=rival,
        terms=list(terms),
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )


def _sign(world, card):
    return apply_terms_card(world, SCENARIO, card, uuid4())


def test_an_alliance_signs_beside_a_trade_deal_and_a_pact() -> None:
    world = _world()
    alliance = make_alliance_term(PLAYER, WRATHFUL_RIVAL, duration_turns=TURNS)
    trade = TradeDealTerm(
        faction_a=PLAYER, faction_b=WRATHFUL_RIVAL, duration_turns=TURNS
    )
    pact = NonAggressionTerm(
        faction_a=PLAYER, faction_b=WRATHFUL_RIVAL, duration_turns=TURNS
    )

    _sign(world, _card(WRATHFUL_RIVAL, alliance, trade, pact))

    kinds = sorted(item.term.kind for item in world.commitments)
    assert kinds == ["alliance", "non_aggression", "trade_deal"]


def test_a_vassalage_signs_beside_a_promise() -> None:
    world = _world()
    vassalage = make_vassal_term(PLAYER, WRATHFUL_RIVAL, duration=TURNS)
    promise = SwornPromiseTerm(
        promisor_id=WRATHFUL_RIVAL,
        beneficiary_id=PLAYER,
        promise=PromiseKind.NEVER_ATTACK_FACTION,
        duration_turns=TURNS,
    )

    _sign(world, _card(WRATHFUL_RIVAL, vassalage, promise))

    assert vassalage_of(world, WRATHFUL_RIVAL) is not None
    assert len(world.commitments) == 2


def test_alliance_and_vassalage_for_one_pair_are_refused_together() -> None:
    world = _world()
    alliance = make_alliance_term(PLAYER, WRATHFUL_RIVAL)
    vassalage = make_vassal_term(PLAYER, WRATHFUL_RIVAL)
    snapshot = world.model_dump(mode="json")

    with pytest.raises(CampaignProgressError):
        _sign(world, _card(WRATHFUL_RIVAL, alliance, vassalage))

    assert world.model_dump(mode="json") == snapshot


def test_the_alliance_ruleset_gate_still_applies() -> None:
    world = _world()
    world.alliance_ruleset = 0

    with pytest.raises(CampaignProgressError):
        _sign(world, _card(WRATHFUL_RIVAL, make_alliance_term(PLAYER, WRATHFUL_RIVAL)))


@pytest.mark.parametrize("rival", [WRATHFUL_RIVAL, CAUTIOUS_RIVAL])
@pytest.mark.parametrize("turns", [0, 4, 12, 40])
def test_alliance_verdict_matches_the_dedicated_acceptance(
    rival: str, turns: int
) -> None:
    world = _world()
    term = make_alliance_term(PLAYER, rival, duration_turns=turns)

    result = evaluate_card(world, SCENARIO, _card(rival, term), None)

    expected = does_counterpart_accept_alliance(world, SCENARIO, term, PLAYER)
    assert (result.verdict is Verdict.ACCEPT) is expected


@pytest.mark.parametrize("rival", [WRATHFUL_RIVAL, CAUTIOUS_RIVAL])
@pytest.mark.parametrize("tribute", [0, 20, 60])
def test_vassal_verdict_matches_the_dedicated_acceptance(
    rival: str, tribute: int
) -> None:
    world = _world()
    term = make_vassal_term(PLAYER, rival, tribute=tribute, duration=8)

    result = evaluate_card(world, SCENARIO, _card(rival, term), None)

    expected = does_counterpart_accept_vassalage(world, SCENARIO, term, PLAYER)
    assert (result.verdict is Verdict.ACCEPT) is expected
