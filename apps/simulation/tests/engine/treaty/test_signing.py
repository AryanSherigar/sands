from uuid import uuid4

import pytest
from app.engine.negotiation import apply_terms_card
from app.engine.treaty.signing import validate_card
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import CommitmentStatus
from strategy_contracts.terms import (
    CedeRegionTerm,
    HostageTerm,
    MilitaryAccessTerm,
    NonAggressionTerm,
    PayGoldTerm,
    PromiseKind,
    SwornPromiseTerm,
    TermsCard,
    TradeDealTerm,
    TributeTerm,
)

from tests.engine.peace.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_peace_card,
    make_world,
    region_owned_by,
    set_score,
    set_war_relation,
)

TURNS = 6


def _world():
    world = make_world()
    world.treaty_ruleset = 1
    return world


def _card(*terms) -> TermsCard:
    return TermsCard(
        proposer_id=PLAYER,
        counterpart_id=WRATHFUL_RIVAL,
        terms=list(terms),
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )


def _pact() -> NonAggressionTerm:
    return NonAggressionTerm(
        faction_a=PLAYER, faction_b=WRATHFUL_RIVAL, duration_turns=TURNS
    )


def _trade() -> TradeDealTerm:
    return TradeDealTerm(
        faction_a=PLAYER, faction_b=WRATHFUL_RIVAL, duration_turns=TURNS
    )


def _promise() -> SwornPromiseTerm:
    return SwornPromiseTerm(
        promisor_id=PLAYER,
        beneficiary_id=WRATHFUL_RIVAL,
        promise=PromiseKind.NEVER_ATTACK_FACTION,
        duration_turns=TURNS,
    )


def _sign(world, card):
    return apply_terms_card(world, SCENARIO, card, uuid4())


def test_pact_trade_and_promise_sign_as_three_commitments() -> None:
    world = _world()

    _sign(world, _card(_pact(), _trade(), _promise()))

    kinds = sorted(commitment.term.kind for commitment in world.commitments)
    assert kinds == ["non_aggression", "sworn_promise", "trade_deal"]
    assert {item.status for item in world.commitments} == {CommitmentStatus.ACTIVE}
    assert {item.end_turn for item in world.commitments} == {world.clock.turn + TURNS}


def test_military_access_and_payment_apply_in_peacetime() -> None:
    world = _world()
    before = world.factions[WRATHFUL_RIVAL].treasury
    access = MilitaryAccessTerm(
        grantor_id=WRATHFUL_RIVAL, grantee_id=PLAYER, duration_turns=TURNS
    )
    payment = PayGoldTerm(payer_id=PLAYER, payee_id=WRATHFUL_RIVAL, amount=30)

    _sign(world, _card(access, payment))

    assert world.factions[WRATHFUL_RIVAL].treasury == before + 30
    assert [item.term.kind for item in world.commitments] == ["military_access"]


def test_one_invalid_clause_leaves_the_world_untouched() -> None:
    world = _world()
    foreign = region_owned_by(world, WRATHFUL_RIVAL)
    bad_cession = CedeRegionTerm(
        from_faction_id=PLAYER, to_faction_id=WRATHFUL_RIVAL, region_id=foreign
    )
    snapshot = world.model_dump(mode="json")

    with pytest.raises(CampaignProgressError):
        _sign(world, _card(_pact(), _trade(), bad_cession))

    assert world.model_dump(mode="json") == snapshot


def test_duplicate_clauses_are_rejected() -> None:
    world = _world()

    with pytest.raises(CampaignProgressError) as raised:
        _sign(world, _card(_pact(), _pact()))

    assert raised.value.code == "duplicate_term"
    assert world.commitments == []


def test_an_active_pact_blocks_a_second_one() -> None:
    world = _world()
    _sign(world, _card(_pact()))

    with pytest.raises(CampaignProgressError) as raised:
        _sign(world, _card(_pact(), _trade()))

    assert raised.value.code == "pact_exists"
    assert len(world.commitments) == 1


def test_hostages_need_a_peace_term() -> None:
    world = _world()
    leader_id = world.factions[PLAYER].leader_id
    hostage = HostageTerm(
        giver_id=PLAYER,
        holder_id=WRATHFUL_RIVAL,
        leader_id=leader_id,
        duration_turns=TURNS,
    )

    with pytest.raises(CampaignProgressError):
        _sign(world, _card(hostage))


def test_a_peace_card_can_carry_a_pact_and_access() -> None:
    world = _world()
    set_war_relation(world, PLAYER, WRATHFUL_RIVAL)
    set_score(add_war(world), attacker=0, defender=90)
    access = MilitaryAccessTerm(
        grantor_id=PLAYER, grantee_id=WRATHFUL_RIVAL, duration_turns=TURNS
    )
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [_pact(), access])

    _sign(world, card)

    assert world.wars == []
    kinds = sorted(item.term.kind for item in world.commitments)
    assert kinds == ["military_access", "non_aggression"]


def test_validate_card_checks_without_changing_the_world() -> None:
    world = _world()
    snapshot = world.model_dump(mode="json")

    validate_card(world, SCENARIO, _card(_pact(), _trade()))

    assert world.model_dump(mode="json") == snapshot


def test_self_dealing_clauses_are_rejected_when_signing() -> None:
    world = _world()
    self_pact = NonAggressionTerm(
        faction_a=PLAYER, faction_b=PLAYER, duration_turns=TURNS
    )

    with pytest.raises(CampaignProgressError):
        _sign(world, _card(self_pact))

    assert world.commitments == []


def test_tribute_beyond_the_payers_treasury_is_rejected() -> None:
    world = _world()
    tribute = TributeTerm(
        payer_id=PLAYER,
        payee_id=WRATHFUL_RIVAL,
        gold_per_turn=world.factions[PLAYER].treasury + 1,
        duration_turns=TURNS,
    )

    with pytest.raises(CampaignProgressError) as raised:
        _sign(world, _card(tribute))

    assert raised.value.code == "cannot_pay"
