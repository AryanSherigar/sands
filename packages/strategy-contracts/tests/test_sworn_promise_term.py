import pytest
from pydantic import ValidationError
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from strategy_contracts.terms import (
    PromiseKind,
    SwornPromiseTerm,
    TermKind,
    TermsCard,
)

PROMISOR = "house_mira"
BENEFICIARY = "house_oren"
THIRD = "house_kessel"


def _term(**overrides: object) -> SwornPromiseTerm:
    fields: dict[str, object] = {
        "promisor_id": PROMISOR,
        "beneficiary_id": BENEFICIARY,
        "promise": PromiseKind.NEVER_ATTACK_FACTION,
        "duration_turns": 5,
    }
    return SwornPromiseTerm(**(fields | overrides))


def test_promisor_and_beneficiary_must_differ() -> None:
    with pytest.raises(ValidationError):
        _term(beneficiary_id=PROMISOR)


def test_never_ally_with_requires_subject() -> None:
    with pytest.raises(ValidationError):
        _term(promise=PromiseKind.NEVER_ALLY_WITH)


def test_subject_forbidden_for_other_kinds() -> None:
    with pytest.raises(ValidationError):
        _term(subject_id=THIRD)
    with pytest.raises(ValidationError):
        _term(promise=PromiseKind.SPARE_PRISONERS, subject_id=THIRD)


def test_never_ally_with_subject_must_differ_from_both_parties() -> None:
    for subject in (PROMISOR, BENEFICIARY):
        with pytest.raises(ValidationError):
            _term(promise=PromiseKind.NEVER_ALLY_WITH, subject_id=subject)
    assert _term(promise=PromiseKind.NEVER_ALLY_WITH, subject_id=THIRD).subject_id


def test_duration_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        _term(duration_turns=0)


def test_term_round_trips_inside_terms_card() -> None:
    card = TermsCard(proposer_id=PROMISOR, counterpart_id=BENEFICIARY, terms=[_term()])
    restored = TermsCard.model_validate(card.model_dump(mode="json"))
    assert restored == card
    assert restored.terms[0].kind == TermKind.SWORN_PROMISE.value


def test_scene_decision_accepts_flat_promise_fields() -> None:
    decision = SceneDecision.model_validate(
        {
            "action": "propose_terms",
            "duration_turns": 4,
            "promise_kind": "never_attack_faction",
            "promise_subject_id": None,
            "is_promise_by_ruler": True,
        }
    )
    assert decision.action is SceneAction.PROPOSE_TERMS
    assert decision.promise_kind is PromiseKind.NEVER_ATTACK_FACTION
    assert decision.is_promise_by_ruler is True


def test_scene_decision_defaults_to_no_promise() -> None:
    decision = SceneDecision(action=SceneAction.CONTINUE_TALK)
    assert decision.promise_kind is None
    assert decision.is_promise_by_ruler is False


def test_never_occupy_region_requires_a_region_subject() -> None:
    with pytest.raises(ValidationError):
        _term(promise=PromiseKind.NEVER_OCCUPY_REGION)
    term = _term(promise=PromiseKind.NEVER_OCCUPY_REGION, subject_id="reg_gate")
    assert term.subject_id == "reg_gate"
