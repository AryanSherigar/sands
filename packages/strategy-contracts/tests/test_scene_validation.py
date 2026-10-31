from builders import make_negotiation_package, make_terms_card
from pydantic import TypeAdapter
from strategy_contracts.scene import SceneOutcome, ScenePackage
from strategy_contracts.scene_validation import (
    validate_outcome_against_package,
    validate_package,
)

OUTCOME_ADAPTER = TypeAdapter(SceneOutcome)
GRADES_SPEC = {"kind": "grades", "rubrics": ["tone", "real_interests"]}
VERDICT_SPEC = {
    "kind": "verdict",
    "options": [{"id": "pardon", "label": "Pardon"}, {"id": "jail", "label": "Jail"}],
}


def _package(
    allowed: list[dict[str, object]], default: dict[str, object]
) -> ScenePackage:
    return ScenePackage.model_validate(
        make_negotiation_package(allowed_outcomes=allowed, default_outcome=default)
    )


def _validate(package: ScenePackage, outcome: dict[str, object]) -> list[str]:
    return validate_outcome_against_package(
        package, OUTCOME_ADAPTER.validate_python(outcome)
    )


def test_grade_out_of_range_is_rejected() -> None:
    package = _package([GRADES_SPEC], {"kind": "grades", "grades": {}})
    assert _validate(package, {"kind": "grades", "grades": {"tone": 9}})


def test_rubric_not_in_spec_is_rejected() -> None:
    package = _package([GRADES_SPEC], {"kind": "grades", "grades": {}})
    assert _validate(package, {"kind": "grades", "grades": {"justification": 2}})


def test_valid_grades_pass() -> None:
    package = _package([GRADES_SPEC], {"kind": "grades", "grades": {}})
    assert (
        _validate(
            package, {"kind": "grades", "grades": {"tone": 4, "real_interests": 0}}
        )
        == []
    )


def test_term_kind_not_allowed_is_rejected() -> None:
    package = ScenePackage.model_validate(make_negotiation_package())
    card = make_terms_card(
        {"kind": "alliance", "faction_a": "house_carrow", "faction_b": "house_ashford"}
    )
    assert _validate(
        package, {"kind": "terms_card", "result": "agreed", "terms_card": card}
    )


def test_agreed_without_card_is_rejected() -> None:
    package = ScenePackage.model_validate(make_negotiation_package())
    assert _validate(package, {"kind": "terms_card", "result": "agreed"})


def test_valid_agreed_outcome_passes() -> None:
    package = ScenePackage.model_validate(make_negotiation_package())
    outcome = {
        "kind": "terms_card",
        "result": "agreed",
        "terms_card": make_terms_card(),
    }
    assert _validate(package, outcome) == []


def test_unknown_verdict_option_is_rejected() -> None:
    package = _package([VERDICT_SPEC], {"kind": "verdict", "option_id": "jail"})
    assert _validate(package, {"kind": "verdict", "option_id": "nope"})


def test_choice_outcome_against_terms_card_only_package_is_rejected() -> None:
    package = ScenePackage.model_validate(make_negotiation_package())
    assert _validate(package, {"kind": "choice", "option_id": "anything"})


def test_default_outcome_that_breaks_its_own_spec_is_flagged() -> None:
    package = _package([VERDICT_SPEC], {"kind": "verdict", "option_id": "nope"})
    assert validate_package(package)


def test_valid_default_outcome_is_clean() -> None:
    assert (
        validate_package(ScenePackage.model_validate(make_negotiation_package())) == []
    )
