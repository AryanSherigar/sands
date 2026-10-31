import pytest
from app.engine import negotiation
from app.engine.negotiation_decision import (
    REASON_MISSING_DURATION,
    REASON_MISSING_SUBJECT,
    REASON_OUTSIDE_LIMITS,
    interpret_decision,
)
from app.services.negotiation_scene import build_negotiation_package
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scene import TermsResult
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from strategy_contracts.terms import (
    NonAggressionTerm,
    PromiseKind,
    SwornPromiseTerm,
    TermKind,
)

from tests.engine.test_negotiation import PLAYER, RIVAL, _world
from tests.models.builders import PLAYTHROUGH_ID  # noqa: F401

SCENARIO = load_three_crowns()


def _package():
    world = _world(["pragmatic"])
    opened = negotiation.open_negotiation(world, RIVAL, "op-1")
    return build_negotiation_package(
        opened, SCENARIO, opened.progress.pending_scene_id, RIVAL
    )


def _decide(action, duration=None):
    return interpret_decision(
        SceneDecision(action=action, duration_turns=duration), _package(), PLAYER, RIVAL
    )


def test_continuing_changes_nothing() -> None:
    assert _decide(SceneAction.CONTINUE_TALK) == _decide(SceneAction.CONTINUE_TALK)
    result = _decide(SceneAction.CONTINUE_TALK)
    assert (result.proposal, result.ending, result.reason) == (None, None, None)


@pytest.mark.parametrize(
    ("action", "ending"),
    [
        (SceneAction.WALK_OUT, TermsResult.WALKED_OUT),
        (SceneAction.REFUSE, TermsResult.REFUSED),
    ],
)
def test_walk_out_and_refusal_end_the_scene(action, ending) -> None:
    assert _decide(action).ending is ending


def test_a_pact_inside_the_range_becomes_a_counterpart_confirmed_card() -> None:
    result = _decide(SceneAction.PROPOSE_TERMS, 12)
    term = result.proposal.terms[0]
    assert isinstance(term, NonAggressionTerm)
    assert (term.duration_turns, result.proposal.is_confirmed_by_counterpart) == (
        12,
        True,
    )
    assert result.proposal.is_confirmed_by_player is False


def test_an_over_long_pact_is_clamped_to_the_cap() -> None:
    result = _decide(SceneAction.PROPOSE_TERMS, 99)
    assert result.proposal.terms[0].duration_turns == negotiation.MAX_PACT_TURNS


def test_a_pact_below_the_range_is_not_proposed() -> None:
    result = _decide(SceneAction.PROPOSE_TERMS, 1)
    assert (result.proposal, result.reason) == (None, REASON_OUTSIDE_LIMITS)


def test_a_proposal_without_a_duration_is_not_proposed() -> None:
    result = _decide(SceneAction.PROPOSE_TERMS)
    assert (result.proposal, result.reason) == (None, REASON_MISSING_DURATION)


def _promise(**fields):
    base = {
        "action": SceneAction.PROPOSE_TERMS,
        "duration_turns": 6,
        "promise_kind": PromiseKind.NEVER_ATTACK_FACTION,
    }
    return interpret_decision(
        SceneDecision(**(base | fields)), _package(), PLAYER, RIVAL
    )


def test_player_promise_builds_a_card_with_the_player_as_promisor() -> None:
    result = _promise()
    term = result.proposal.terms[0]
    assert isinstance(term, SwornPromiseTerm)
    assert (term.promisor_id, term.beneficiary_id) == (PLAYER, RIVAL)
    assert (term.promise, term.duration_turns) == (
        PromiseKind.NEVER_ATTACK_FACTION,
        6,
    )
    assert result.proposal.is_confirmed_by_counterpart is True


def test_ruler_promise_flips_promisor_and_beneficiary() -> None:
    term = _promise(is_promise_by_ruler=True).proposal.terms[0]
    assert (term.promisor_id, term.beneficiary_id) == (RIVAL, PLAYER)


def test_promise_ignores_the_pact_acceptance_limits() -> None:
    assert _promise(duration_turns=1).proposal is not None


def test_promise_without_duration_is_rejected() -> None:
    result = _promise(duration_turns=None)
    assert (result.proposal, result.reason) == (None, REASON_MISSING_DURATION)


def test_never_ally_without_subject_is_rejected() -> None:
    result = _promise(promise_kind=PromiseKind.NEVER_ALLY_WITH)
    assert (result.proposal, result.reason) == (None, REASON_MISSING_SUBJECT)


def test_never_ally_with_subject_is_proposed() -> None:
    result = _promise(
        promise_kind=PromiseKind.NEVER_ALLY_WITH, promise_subject_id="house_mira"
    )
    assert result.proposal.terms[0].subject_id == "house_mira"


def test_promise_duration_is_capped() -> None:
    term = _promise(duration_turns=999).proposal.terms[0]
    assert term.duration_turns == negotiation.MAX_PACT_TURNS


def test_package_allows_and_prices_sworn_promises_at_zero() -> None:
    spec = _package().allowed_outcomes[0]
    assert TermKind.SWORN_PROMISE in spec.allowed_term_kinds
    assert spec.allowed_term_kinds.count(TermKind.SWORN_PROMISE) == 1
    assert spec.price_by_term_kind[TermKind.SWORN_PROMISE] == 0


def test_package_lists_other_realms_so_a_subject_can_be_named() -> None:
    facts = {fact.label: fact.value for fact in _package().situation.facts}
    others = sorted(
        faction_id
        for faction_id in _world(["pragmatic"]).factions
        if faction_id not in (PLAYER, RIVAL)
    )
    assert facts["Other realms"] == ", ".join(others)
