from app.engine import negotiation
from app.engine.negotiation_decision import (
    REASON_MISSING_DURATION,
    REASON_NOT_ALLOWED,
)
from app.engine.treaty.interpretation import (
    REASON_CANNOT_PAY,
    REASON_INVALID_TERMS,
    interpret_card_decision,
)
from app.services.negotiation_scene import build_negotiation_package
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from strategy_contracts.terms import (
    CedeRegionTerm,
    NonAggressionTerm,
    PayGoldTerm,
    PromiseKind,
    SwornPromiseTerm,
    TermKind,
    TradeDealTerm,
    TributeTerm,
)
from strategy_contracts.treaty import Verdict

from tests.engine.test_negotiation import PLAYER, RIVAL, _world

SCENARIO = load_three_crowns()
PROPOSE = SceneAction.PROPOSE_TERMS
OUTSIDE = "house_outsider"


def _setup(ruleset: int = 1):
    world = _world(["wrathful"])
    world.treaty_ruleset = ruleset
    opened = negotiation.open_negotiation(world, RIVAL, "op-1")
    package = build_negotiation_package(
        opened, SCENARIO, opened.progress.pending_scene_id, RIVAL
    )
    return opened, package


def _decide(ruleset: int = 1, **fields):
    world, package = _setup(ruleset)
    decision = SceneDecision(**({"action": PROPOSE} | fields))
    return interpret_card_decision(decision, package, world, SCENARIO, PLAYER, RIVAL)


def _pact(turns: int) -> NonAggressionTerm:
    return NonAggressionTerm(faction_a=PLAYER, faction_b=RIVAL, duration_turns=turns)


def _trade(turns: int) -> TradeDealTerm:
    return TradeDealTerm(faction_a=PLAYER, faction_b=RIVAL, duration_turns=turns)


def test_a_multi_clause_card_inside_the_range_becomes_one_proposal() -> None:
    result = _decide(terms=[_pact(9), _trade(12)])

    assert [term.kind for term in result.proposal.terms] == [
        "non_aggression",
        "trade_deal",
    ]
    assert result.verdict is Verdict.ACCEPT
    assert result.proposal.is_confirmed_by_counterpart is True


def test_a_card_between_the_lines_haggles_and_names_the_verdict() -> None:
    result = _decide(terms=[_pact(6)])

    assert (result.proposal, result.reason) == (None, "haggle")
    assert result.verdict is Verdict.HAGGLE


def test_flat_duration_still_builds_the_legacy_pact() -> None:
    result = _decide(duration_turns=12)

    assert result.proposal.terms[0] == _pact(12)


def test_flat_promise_joins_the_clauses() -> None:
    result = _decide(
        terms=[_pact(12)],
        promise_kind=PromiseKind.NEVER_ATTACK_FACTION,
        duration_turns=6,
    )

    kinds = [type(term) for term in result.proposal.terms]
    assert kinds == [NonAggressionTerm, SwornPromiseTerm]


def test_demanding_card_is_refused_with_nothing_proposed() -> None:
    demands = [PayGoldTerm(payer_id=RIVAL, payee_id=PLAYER, amount=900)] * 3

    result = _decide(terms=demands)

    assert (result.proposal, result.verdict) == (None, Verdict.REFUSE)


def test_terms_naming_a_third_realm_are_invalid() -> None:
    stranger = NonAggressionTerm(faction_a=PLAYER, faction_b=OUTSIDE, duration_turns=6)

    result = _decide(terms=[stranger])

    assert (result.proposal, result.reason) == (None, REASON_INVALID_TERMS)


def test_over_long_durations_are_clamped() -> None:
    result = _decide(terms=[_pact(99), _trade(99)])

    assert {term.duration_turns for term in result.proposal.terms} == {
        negotiation.MAX_PACT_TURNS
    }


def test_trade_is_not_allowed_below_the_treaty_ruleset() -> None:
    result = _decide(ruleset=0, terms=[_trade(12)])

    assert (result.proposal, result.reason) == (None, REASON_NOT_ALLOWED)


def test_no_clauses_and_no_duration_is_missing_a_duration() -> None:
    assert _decide().reason == REASON_MISSING_DURATION


def test_a_clause_the_world_cannot_sign_is_invalid() -> None:
    world, _ = _setup()
    foreign = next(
        key for key, region in world.regions.items() if region.owner_id == RIVAL
    )
    cession = CedeRegionTerm(
        from_faction_id=PLAYER, to_faction_id=RIVAL, region_id=foreign
    )

    result = _decide(terms=[_pact(12), cession])

    assert (result.proposal, result.reason) == (None, REASON_INVALID_TERMS)


def test_war_only_clauses_are_not_offered_in_peacetime_scenes() -> None:
    _, package = _setup()
    kinds = package.allowed_outcomes[0].allowed_term_kinds

    assert not {TermKind.HOSTAGE, TermKind.RELEASE_PRISONERS, TermKind.PEACE} & set(
        kinds
    )
    assert {TermKind.TRADE_DEAL, TermKind.MILITARY_ACCESS} <= set(kinds)


def test_ruleset_one_packages_name_both_realms_for_the_narrator() -> None:
    _, package = _setup()
    facts = {fact.label: fact.value for fact in package.situation.facts}

    assert facts["Your realm id"] == RIVAL
    assert facts["The player's realm id"] == PLAYER


def test_legacy_packages_carry_no_realm_ids() -> None:
    _, package = _setup(ruleset=0)

    assert "Your realm id" not in {fact.label for fact in package.situation.facts}


def test_clauses_that_name_one_realm_twice_are_invalid() -> None:
    self_pact = NonAggressionTerm(faction_a=PLAYER, faction_b=PLAYER, duration_turns=12)
    self_trade = TradeDealTerm(faction_a=PLAYER, faction_b=PLAYER, duration_turns=12)
    self_tribute = TributeTerm(
        payer_id=PLAYER, payee_id=PLAYER, gold_per_turn=50, duration_turns=12
    )

    for term in (self_pact, self_trade, self_tribute):
        result = _decide(terms=[term])
        assert (result.proposal, result.reason) == (None, REASON_INVALID_TERMS)


def test_tribute_the_payer_cannot_cover_is_invalid() -> None:
    world, _ = _setup()
    tribute = TributeTerm(
        payer_id=PLAYER,
        payee_id=RIVAL,
        gold_per_turn=world.factions[PLAYER].treasury + 1,
        duration_turns=12,
    )

    result = _decide(terms=[tribute, _pact(12)])

    assert result.proposal is None


def test_a_card_the_ruler_would_sign_but_the_payer_cannot_afford_haggles() -> None:
    world, _ = _setup()
    treasury = world.factions[PLAYER].treasury
    payment = PayGoldTerm(payer_id=PLAYER, payee_id=RIVAL, amount=treasury - 5)
    tribute = TributeTerm(
        payer_id=PLAYER, payee_id=RIVAL, gold_per_turn=20, duration_turns=12
    )

    result = _decide(terms=[_pact(12), payment, tribute])

    assert result.proposal is None
    assert result.verdict is Verdict.HAGGLE
    assert result.reason == REASON_CANNOT_PAY


def test_the_narrator_is_told_what_the_player_can_pay() -> None:
    world, package = _setup()
    facts = {fact.label: fact.value for fact in package.situation.facts}

    assert facts["The player's treasury"] == f"{world.factions[PLAYER].treasury} gold"
