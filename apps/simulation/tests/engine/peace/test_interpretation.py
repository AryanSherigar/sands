from uuid import uuid4

from app.engine.negotiation_decision import REASON_OUTSIDE_LIMITS
from app.engine.peace.interpretation import (
    REASON_INVALID_TERMS,
    REASON_MISSING_TIER,
    REASON_NO_WAR,
    interpret_peace_decision,
)
from app.services.negotiation_scene import build_peace_package
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scene import SceneType, TermsResult
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from strategy_contracts.terms import (
    CedeRegionTerm,
    PayGoldTerm,
    PeaceTerm,
    TributeTerm,
)

from tests.engine.peace.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
    region_owned_by,
    set_score,
)

PROPOSE = SceneAction.PROPOSE_TERMS


def _interpret(world, decision: SceneDecision):
    package = build_peace_package(world, SCENARIO, uuid4(), WRATHFUL_RIVAL)
    return package, interpret_peace_decision(
        decision, package, world, SCENARIO, PLAYER, WRATHFUL_RIVAL
    )


def test_package_is_a_peace_scene_with_peace_terms() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=33)

    package, _ = _interpret(world, SceneDecision(action=SceneAction.CONTINUE_TALK))

    assert package.scene_type is SceneType.PEACE
    assert package.allowed_outcomes[0].war_score_available == 33


def test_winner_gets_a_proposal_the_counterpart_accepts() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=90)

    _, result = _interpret(
        world, SceneDecision(action=PROPOSE, peace_tier=PeaceTier.SHORT)
    )

    assert result.proposal is not None
    assert result.proposal.terms[0].tier == PeaceTier.SHORT


def test_leading_counterpart_refuses_a_bare_peace() -> None:
    world = make_world()
    set_score(add_war(world), attacker=90, defender=0)

    _, result = _interpret(
        world, SceneDecision(action=PROPOSE, peace_tier=PeaceTier.SHORT)
    )

    assert (result.proposal, result.reason) == (None, REASON_OUTSIDE_LIMITS)


def test_conceding_gold_buys_peace_from_a_leading_counterpart() -> None:
    world = make_world()
    set_score(add_war(world), attacker=40, defender=0)
    world.factions[PLAYER].treasury = 10_000
    gold = PayGoldTerm(payer_id=PLAYER, payee_id=WRATHFUL_RIVAL, amount=6000)

    _, result = _interpret(
        world,
        SceneDecision(action=PROPOSE, peace_tier=PeaceTier.SHORT, terms=[gold]),
    )

    assert result.proposal is not None


def test_missing_tier_is_reported() -> None:
    world = make_world()
    add_war(world)

    _, result = _interpret(world, SceneDecision(action=PROPOSE))

    assert result.reason == REASON_MISSING_TIER


def test_no_war_is_reported() -> None:
    world = make_world()
    add_war(world, attacker_id="house_carrow", defender_id=PLAYER)
    package = build_peace_package(world, SCENARIO, uuid4(), "house_carrow")

    result = interpret_peace_decision(
        SceneDecision(action=PROPOSE, peace_tier=PeaceTier.SHORT),
        package,
        world,
        SCENARIO,
        PLAYER,
        WRATHFUL_RIVAL,
    )

    assert result.reason == REASON_NO_WAR


def test_walking_out_ends_the_scene() -> None:
    world = make_world()
    add_war(world)

    _, result = _interpret(world, SceneDecision(action=SceneAction.WALK_OUT))

    assert result.ending is TermsResult.WALKED_OUT


def test_extra_peace_terms_from_the_model_are_dropped() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=90)
    extra = PeaceTerm(
        faction_a=PLAYER, faction_b=WRATHFUL_RIVAL, tier=PeaceTier.PERPETUAL
    )

    _, result = _interpret(
        world,
        SceneDecision(action=PROPOSE, peace_tier=PeaceTier.SHORT, terms=[extra]),
    )

    assert result.proposal is not None
    kinds = [term.kind for term in result.proposal.terms]
    assert kinds == ["peace"]
    assert result.proposal.terms[0].tier == PeaceTier.SHORT


def _winning_world():
    world = make_world()
    set_score(add_war(world), attacker=0, defender=90)
    return world


def test_a_ceded_region_the_player_owns_is_kept_on_the_card() -> None:
    world = _winning_world()
    cession = CedeRegionTerm(
        from_faction_id=PLAYER,
        to_faction_id=WRATHFUL_RIVAL,
        region_id=region_owned_by(world, PLAYER),
    )

    _, result = _interpret(
        world,
        SceneDecision(action=PROPOSE, peace_tier=PeaceTier.SHORT, terms=[cession]),
    )

    assert [term.kind for term in result.proposal.terms] == ["peace", "cede_region"]


def test_a_cession_of_land_the_player_does_not_hold_is_not_proposed() -> None:
    world = _winning_world()
    cession = CedeRegionTerm(
        from_faction_id=PLAYER,
        to_faction_id=WRATHFUL_RIVAL,
        region_id=region_owned_by(world, WRATHFUL_RIVAL),
    )

    _, result = _interpret(
        world,
        SceneDecision(action=PROPOSE, peace_tier=PeaceTier.SHORT, terms=[cession]),
    )

    assert (result.proposal, result.reason) == (None, REASON_INVALID_TERMS)


def test_gold_the_payer_cannot_afford_is_not_proposed() -> None:
    world = _winning_world()
    world.factions[PLAYER].treasury = 10
    gold = PayGoldTerm(payer_id=PLAYER, payee_id=WRATHFUL_RIVAL, amount=500)

    _, result = _interpret(
        world,
        SceneDecision(action=PROPOSE, peace_tier=PeaceTier.SHORT, terms=[gold]),
    )

    assert (result.proposal, result.reason) == (None, REASON_INVALID_TERMS)


def test_term_kinds_outside_the_agreed_vocabulary_are_dropped() -> None:
    world = _winning_world()
    world.treaty_ruleset = 0
    tribute = TributeTerm(
        payer_id=PLAYER, payee_id=WRATHFUL_RIVAL, gold_per_turn=5, duration_turns=3
    )

    _, result = _interpret(
        world,
        SceneDecision(action=PROPOSE, peace_tier=PeaceTier.SHORT, terms=[tribute]),
    )

    assert [term.kind for term in result.proposal.terms] == ["peace"]


def test_the_package_carries_a_peace_brief_for_the_narrator() -> None:
    world = _winning_world()

    package, _ = _interpret(world, SceneDecision(action=SceneAction.CONTINUE_TALK))

    brief = package.hidden_limits.peace_brief
    assert brief.counterpart_faction_id == WRATHFUL_RIVAL


def test_treaty_ruleset_keeps_tribute_and_trade_clauses() -> None:
    world = _winning_world()
    world.treaty_ruleset = 1
    tribute = TributeTerm(
        payer_id=PLAYER, payee_id=WRATHFUL_RIVAL, gold_per_turn=5, duration_turns=3
    )

    _, result = _interpret(
        world,
        SceneDecision(action=PROPOSE, peace_tier=PeaceTier.SHORT, terms=[tribute]),
    )

    assert [term.kind for term in result.proposal.terms] == ["peace", "tribute"]
    assert result.verdict.value == "accept"


def test_treaty_ruleset_refuses_self_dealing_and_uncovered_tribute_in_peace() -> None:
    world = _winning_world()
    world.treaty_ruleset = 1
    self_tribute = TributeTerm(
        payer_id=PLAYER, payee_id=PLAYER, gold_per_turn=5, duration_turns=3
    )
    broke = TributeTerm(
        payer_id=PLAYER,
        payee_id=WRATHFUL_RIVAL,
        gold_per_turn=world.factions[PLAYER].treasury + 1,
        duration_turns=3,
    )

    for term in (self_tribute, broke):
        _, result = _interpret(
            world,
            SceneDecision(action=PROPOSE, peace_tier=PeaceTier.SHORT, terms=[term]),
        )
        assert (result.proposal, result.reason) == (None, REASON_INVALID_TERMS)


def test_a_peace_package_allows_conditional_clauses_only_from_treaty_ruleset_1() -> (
    None
):
    legacy = make_world()
    legacy.treaty_ruleset = 0
    set_score(add_war(legacy), attacker=0, defender=33)
    modern = make_world()
    modern.treaty_ruleset = 1
    set_score(add_war(modern), attacker=0, defender=33)

    legacy_package, _ = _interpret(
        legacy, SceneDecision(action=SceneAction.CONTINUE_TALK)
    )
    modern_package, _ = _interpret(
        modern, SceneDecision(action=SceneAction.CONTINUE_TALK)
    )

    assert "conditional" not in legacy_package.allowed_outcomes[0].allowed_term_kinds
    assert "conditional" in modern_package.allowed_outcomes[0].allowed_term_kinds
