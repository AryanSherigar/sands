from collections.abc import Callable

from strategy_contracts.limits import MAX_OUTCOME_GRADE
from strategy_contracts.scene import (
    ChoiceOutcome,
    ChoiceSpec,
    GradesOutcome,
    GradesSpec,
    ProseOnlyOutcome,
    ProseOnlySpec,
    ScenePackage,
    TermsCardOutcome,
    TermsCardSpec,
    TermsResult,
    VerdictOutcome,
    VerdictSpec,
)

OutcomeSpecType = TermsCardSpec | GradesSpec | VerdictSpec | ChoiceSpec | ProseOnlySpec
OutcomeType = (
    TermsCardOutcome | GradesOutcome | VerdictOutcome | ChoiceOutcome | ProseOnlyOutcome
)


def _validate_terms(spec: TermsCardSpec, outcome: TermsCardOutcome) -> list[str]:
    reasons: list[str] = []
    if outcome.result is TermsResult.AGREED and outcome.terms_card is None:
        reasons.append("an agreed outcome needs a terms card")
    if outcome.terms_card is None:
        return reasons
    allowed = {kind.value for kind in spec.allowed_term_kinds}
    reasons += [
        f"term kind '{term.kind}' is not allowed for this scene"
        for term in outcome.terms_card.terms
        if term.kind not in allowed
    ]
    return reasons


def _validate_grades(spec: GradesSpec, outcome: GradesOutcome) -> list[str]:
    reasons = [
        f"rubric '{rubric.value}' is not graded in this scene"
        for rubric in outcome.grades
        if rubric not in spec.rubrics
    ]
    reasons += [
        f"grade {value} for '{rubric.value}' is outside 0..{MAX_OUTCOME_GRADE}"
        for rubric, value in outcome.grades.items()
        if not 0 <= value <= MAX_OUTCOME_GRADE
    ]
    return reasons


def _validate_option(
    spec: VerdictSpec | ChoiceSpec, outcome: VerdictOutcome | ChoiceOutcome
) -> list[str]:
    if outcome.option_id in {option.id for option in spec.options}:
        return []
    return [f"option '{outcome.option_id}' is not offered in this scene"]


def _validate_prose_only(spec: ProseOnlySpec, outcome: ProseOnlyOutcome) -> list[str]:
    return []


_VALIDATORS: dict[str, Callable[[OutcomeSpecType, OutcomeType], list[str]]] = {
    "terms_card": _validate_terms,
    "grades": _validate_grades,
    "verdict": _validate_option,
    "choice": _validate_option,
    "prose_only": _validate_prose_only,
}


def validate_outcome_against_package(
    package: ScenePackage, outcome: OutcomeType
) -> list[str]:
    spec = next(
        (item for item in package.allowed_outcomes if item.kind == outcome.kind), None
    )
    if spec is None:
        return [f"outcome kind '{outcome.kind}' is not allowed for this scene"]
    return _VALIDATORS[outcome.kind](spec, outcome)


def validate_package(package: ScenePackage) -> list[str]:
    return validate_outcome_against_package(package, package.default_outcome)
