from app.engine import negotiation
from app.services.negotiation_scene import build_negotiation_package
from app.services.scene_kinds import interpret_scene_decision
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from strategy_contracts.terms import NonAggressionTerm, TradeDealTerm
from strategy_contracts.treaty import Verdict
from tests.engine.test_negotiation import PLAYER, RIVAL, _world

SCENARIO = load_three_crowns()


def _scene(ruleset: int):
    world = _world(["wrathful"])
    world.treaty_ruleset = ruleset
    opened = negotiation.open_negotiation(world, RIVAL, "op-1")
    package = build_negotiation_package(
        opened, SCENARIO, opened.progress.pending_scene_id, RIVAL
    )
    leader_id = world.factions[RIVAL].leader_id
    package.participants[0].participant_id = leader_id
    return opened, package


def _decision(turns: int) -> SceneDecision:
    terms = [
        NonAggressionTerm(faction_a=PLAYER, faction_b=RIVAL, duration_turns=turns),
        TradeDealTerm(faction_a=PLAYER, faction_b=RIVAL, duration_turns=turns),
    ]
    return SceneDecision(action=SceneAction.PROPOSE_TERMS, terms=terms)


def test_treaty_ruleset_routes_negotiation_through_the_ledger() -> None:
    world, package = _scene(ruleset=1)

    result = interpret_scene_decision(_decision(12), package, world, SCENARIO)

    assert [term.kind for term in result.proposal.terms] == [
        "non_aggression",
        "trade_deal",
    ]
    assert (result.verdict, len(result.bands)) == (Verdict.ACCEPT, 2)


def test_a_card_that_only_bargains_reports_haggle() -> None:
    world, package = _scene(ruleset=1)

    pact = NonAggressionTerm(faction_a=PLAYER, faction_b=RIVAL, duration_turns=6)
    decision = SceneDecision(action=SceneAction.PROPOSE_TERMS, terms=[pact])

    result = interpret_scene_decision(decision, package, world, SCENARIO)

    assert (result.proposal, result.reason) == (None, "haggle")
    assert result.verdict is Verdict.HAGGLE


def test_legacy_ruleset_ignores_extra_clauses() -> None:
    world, package = _scene(ruleset=0)

    result = interpret_scene_decision(_decision(12), package, world, SCENARIO)

    assert result.proposal is None
    assert result.verdict is None
