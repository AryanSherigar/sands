import pytest
from pydantic import TypeAdapter, ValidationError
from strategy_contracts.limits import MAX_CONDITIONAL_EXPIRY_TURNS
from strategy_contracts.terms import ConditionalMode, ConditionalTerm, Term


def _tribute() -> dict[str, object]:
    return {
        "kind": "tribute",
        "payer_id": "aa",
        "payee_id": "bb",
        "gold_per_turn": 2,
        "duration_turns": 3,
    }


def _conditional(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "kind": "conditional",
        "mode": "trigger",
        "when": {"template": "treasury_above", "faction_id": "aa", "value": 50},
        "expires_in_turns": 10,
        "inner": _tribute(),
    }
    return {**base, **overrides}


def test_conditional_term_parses_through_term_union() -> None:
    term = TypeAdapter(Term).validate_python(_conditional())
    assert isinstance(term, ConditionalTerm)
    assert term.mode is ConditionalMode.TRIGGER
    assert term.inner.kind == "tribute"


def test_gate_mode_is_accepted() -> None:
    term = ConditionalTerm.model_validate(_conditional(mode="gate"))
    assert term.mode is ConditionalMode.GATE


def test_conditionals_do_not_nest() -> None:
    nested = _conditional(inner=_conditional())
    with pytest.raises(ValidationError):
        ConditionalTerm.model_validate(nested)


@pytest.mark.parametrize("turns", [0, MAX_CONDITIONAL_EXPIRY_TURNS + 1])
def test_expiry_is_bounded(turns: int) -> None:
    with pytest.raises(ValidationError):
        ConditionalTerm.model_validate(_conditional(expires_in_turns=turns))


def test_unknown_mode_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ConditionalTerm.model_validate(_conditional(mode="sometimes"))


def test_peace_terms_cannot_be_conditional() -> None:
    peace = {"kind": "peace", "faction_a": "aa", "faction_b": "bb", "tier": "short"}
    with pytest.raises(ValidationError):
        ConditionalTerm.model_validate(_conditional(inner=peace))


def test_gate_needs_an_ongoing_clause() -> None:
    alliance = {"kind": "alliance", "faction_a": "aa", "faction_b": "bb"}
    with pytest.raises(ValidationError):
        ConditionalTerm.model_validate(_conditional(mode="gate", inner=alliance))
    ConditionalTerm.model_validate(_conditional(mode="trigger", inner=alliance))


def test_condition_faction_must_be_a_party() -> None:
    other = {"template": "treasury_above", "faction_id": "cc", "value": 5}
    with pytest.raises(ValidationError):
        ConditionalTerm.model_validate(_conditional(when=other))
