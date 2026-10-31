import pytest
from builders import make_terms_card
from pydantic import TypeAdapter, ValidationError
from strategy_contracts.terms import Term, TermsCard

TERM_EXAMPLES = [
    {
        "kind": "cede_region",
        "from_faction_id": "aa",
        "to_faction_id": "bb",
        "region_id": "rr",
    },
    {"kind": "pay_gold", "payer_id": "aa", "payee_id": "bb", "amount": 10},
    {
        "kind": "tribute",
        "payer_id": "aa",
        "payee_id": "bb",
        "gold_per_turn": 2,
        "duration_turns": 3,
    },
    {
        "kind": "release_prisoners",
        "holder_id": "aa",
        "recipient_id": "bb",
        "prisoner_ids": ["pp"],
    },
    {
        "kind": "non_aggression",
        "faction_a": "aa",
        "faction_b": "bb",
        "duration_turns": 4,
    },
    {"kind": "alliance", "faction_a": "aa", "faction_b": "bb"},
    {
        "kind": "military_access",
        "grantor_id": "aa",
        "grantee_id": "bb",
        "duration_turns": 2,
    },
    {"kind": "trade_deal", "faction_a": "aa", "faction_b": "bb", "duration_turns": 5},
    {
        "kind": "hostage",
        "giver_id": "aa",
        "holder_id": "bb",
        "leader_id": "ll",
        "duration_turns": 6,
    },
]
TERM_ADAPTER = TypeAdapter(Term)


@pytest.mark.parametrize("payload", TERM_EXAMPLES, ids=lambda p: p["kind"])
def test_each_term_kind_round_trips(payload: dict[str, object]) -> None:
    term = TERM_ADAPTER.validate_python(payload)
    assert TERM_ADAPTER.validate_json(TERM_ADAPTER.dump_json(term)) == term


def test_unknown_term_kind_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TERM_ADAPTER.validate_python({"kind": "marriage"})


def test_card_needs_between_one_and_eight_terms() -> None:
    card = make_terms_card()
    term = card["terms"][0]
    with pytest.raises(ValidationError):
        TermsCard.model_validate({**card, "terms": []})
    with pytest.raises(ValidationError):
        TermsCard.model_validate({**card, "terms": [term] * 9})
