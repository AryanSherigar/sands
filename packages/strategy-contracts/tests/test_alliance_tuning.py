import pytest
from pydantic import ValidationError
from strategy_contracts.alliance import AllianceTuning, AllianceType
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.negotiation_rules import NegotiationRules
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scenario import Tuning
from strategy_contracts.terms import AllianceTerm, PeaceTerm, TermKind, TermsCard

FOREVER = 0


def test_defaults_load_for_legacy_scenario() -> None:
    scenario = load_three_crowns()

    assert scenario.tuning.alliance == AllianceTuning()


def test_alliance_term_round_trips_with_new_fields() -> None:
    term = AllianceTerm(
        faction_a="aa",
        faction_b="bb",
        alliance_type=AllianceType.OFFENSIVE,
        duration_turns=12,
        is_separate_peace_banned=True,
    )

    card = TermsCard.model_validate(
        {
            "proposer_id": "aa",
            "counterpart_id": "bb",
            "terms": [term.model_dump(mode="json")],
        }
    )

    assert card.terms[0] == term


def test_legacy_alliance_term_defaults_to_defensive_forever() -> None:
    term = AllianceTerm(faction_a="aa", faction_b="bb")

    assert term.alliance_type == AllianceType.DEFENSIVE
    assert term.duration_turns == FOREVER
    assert term.is_separate_peace_banned is False


def test_refusal_cost_higher_for_defensive() -> None:
    tuning = Tuning().alliance

    assert tuning.refusal_opinion_cost_defensive > tuning.refusal_opinion_cost_offensive
    with pytest.raises(ValidationError):
        AllianceTuning(
            refusal_opinion_cost_offensive=10, refusal_opinion_cost_defensive=5
        )


def test_zero_refusals_to_break_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AllianceTuning(refusal_breaks_alliance_after=0)


def test_alliance_kind_is_allowed_in_negotiation_rules() -> None:
    rules = NegotiationRules(allowed_term_kinds=[TermKind.ALLIANCE])

    assert rules.allowed_term_kinds == [TermKind.ALLIANCE]


def test_peace_term_party_ids_default_to_the_two_principals_only() -> None:
    term = PeaceTerm(faction_a="aa", faction_b="bb", tier=PeaceTier.SHORT)

    assert term.party_ids == []
    named = term.model_copy(update={"party_ids": ["cc"]})
    assert PeaceTerm.model_validate(named.model_dump(mode="json")).party_ids == ["cc"]
