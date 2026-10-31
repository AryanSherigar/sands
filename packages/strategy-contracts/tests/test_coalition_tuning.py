import pytest
from pydantic import TypeAdapter, ValidationError
from strategy_contracts.coalition import (
    AppeaseOffer,
    ClaimCessionOffer,
    CoalitionTuning,
    GoldOffer,
    PactOffer,
)
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scenario import Tuning


def test_defaults_load_for_legacy_scenario() -> None:
    assert load_three_crowns().tuning.coalition == CoalitionTuning()


def test_tuning_mounts_on_scenario_tuning() -> None:
    assert Tuning().coalition.min_members == 2


def test_a_coalition_needs_at_least_two_members() -> None:
    with pytest.raises(ValidationError):
        CoalitionTuning(min_members=1)


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        CoalitionTuning.model_validate({"surprise": 1})


def test_appease_tuning_defaults_exist() -> None:
    tuning = CoalitionTuning()

    assert tuning.appease_cooldown_turns >= 1
    assert tuning.appease_rejoin_lockout_turns >= 1
    assert tuning.appease_max_pact_turns >= 1
    assert tuning.appease_cession_value_divisor >= 1


def test_a_pact_alone_cannot_buy_out_a_resentful_member() -> None:
    tuning = CoalitionTuning()
    resentful_price = tuning.appease_base_price + tuning.appease_opinion_weight * 20

    assert tuning.appease_pact_max_value < resentful_price


def test_appease_offer_discriminates_on_kind() -> None:
    adapter = TypeAdapter(AppeaseOffer)

    assert isinstance(adapter.validate_python({"kind": "gold", "amount": 5}), GoldOffer)
    assert isinstance(
        adapter.validate_python({"kind": "pact", "duration_turns": 4}), PactOffer
    )
    assert isinstance(
        adapter.validate_python({"kind": "claim_cession", "region_id": "r1"}),
        ClaimCessionOffer,
    )
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "gold"})
