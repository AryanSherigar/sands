import pytest
from pydantic import ValidationError
from strategy_contracts.ai import AiTuning
from strategy_contracts.examples import load_three_crowns_expanded
from strategy_contracts.scenario import Tuning


def test_tuning_ai_defaults() -> None:
    assert Tuning().ai == AiTuning(
        trait_weight=1, stance_weight=10, variance_margin=5, minimum_score=1
    )


@pytest.mark.parametrize(
    "field", ["trait_weight", "stance_weight", "variance_margin", "minimum_score"]
)
def test_ai_tuning_rejects_negative_values(field: str) -> None:
    with pytest.raises(ValidationError):
        AiTuning.model_validate({field: -1})


def test_existing_scenario_documents_still_validate() -> None:
    assert load_three_crowns_expanded().tuning.ai == AiTuning()


def test_aim_tuning_defaults() -> None:
    tuning = AiTuning()

    assert (tuning.aim_bonus, tuning.aim_max_turns) == (8, 12)
    assert (tuning.situation_bonus, tuning.low_treasury, tuning.low_stability) == (
        6,
        50,
        40,
    )


@pytest.mark.parametrize(
    "field", ["aim_bonus", "situation_bonus", "low_treasury", "low_stability"]
)
def test_aim_tuning_rejects_negative_values(field: str) -> None:
    with pytest.raises(ValidationError):
        AiTuning.model_validate({field: -1})


def test_aim_max_turns_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        AiTuning.model_validate({"aim_max_turns": 0})


def test_home_life_tuning_defaults() -> None:
    tuning = AiTuning()

    assert (tuning.loan_cap, tuning.min_levy, tuning.max_levy) == (200, 20, 60)
    assert (tuning.levy_friction, tuning.disband_below_troops) == (4, 30)


@pytest.mark.parametrize("field", ["loan_cap", "levy_friction", "disband_below_troops"])
def test_home_life_tuning_rejects_negative_values(field: str) -> None:
    with pytest.raises(ValidationError):
        AiTuning.model_validate({field: -1})


@pytest.mark.parametrize("field", ["min_levy", "max_levy"])
def test_levy_sizes_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        AiTuning.model_validate({field: 0})


def test_military_tuning_defaults() -> None:
    tuning = AiTuning()

    assert (tuning.strike_bonus, tuning.approach_bonus, tuning.defense_bonus) == (
        4,
        2,
        6,
    )
    assert (tuning.risk_penalty, tuning.merge_bonus, tuning.scout_stale_turns) == (
        8,
        2,
        6,
    )
    assert (tuning.feint_min_cunning, tuning.feint_bonus) == (2, 4)
    assert (tuning.supply_strained_penalty, tuning.supply_isolated_penalty) == (3, 6)


@pytest.mark.parametrize(
    "field",
    [
        "strike_bonus",
        "approach_bonus",
        "defense_bonus",
        "risk_penalty",
        "merge_bonus",
        "feint_bonus",
        "supply_strained_penalty",
        "supply_isolated_penalty",
    ],
)
def test_military_tuning_rejects_negative_values(field: str) -> None:
    with pytest.raises(ValidationError):
        AiTuning.model_validate({field: -1})


def test_scout_stale_turns_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        AiTuning.model_validate({"scout_stale_turns": 0})


def test_diplomacy_tuning_defaults() -> None:
    tuning = AiTuning()

    assert (tuning.war_base_bonus, tuning.ground_strength_divisor) == (4, 10)
    assert (tuning.ratio_divisor, tuning.second_front_penalty) == (20, 4)
    assert (tuning.demand_gold, tuning.demand_min_ratio) == (30, 120)
    assert (tuning.aim_target_bonus, tuning.forgery_bonus) == (4, 2)


@pytest.mark.parametrize(
    "field",
    [
        "war_base_bonus",
        "second_front_penalty",
        "demand_gold",
        "demand_min_ratio",
        "aim_target_bonus",
        "forgery_bonus",
    ],
)
def test_diplomacy_tuning_rejects_negative_values(field: str) -> None:
    with pytest.raises(ValidationError):
        AiTuning.model_validate({field: -1})


@pytest.mark.parametrize("field", ["ground_strength_divisor", "ratio_divisor"])
def test_divisors_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        AiTuning.model_validate({field: 0})


def test_stability_and_army_cap_defaults() -> None:
    tuning = AiTuning()

    assert (tuning.uprising_bonus, tuning.max_armies) == (10, 6)


def test_uprising_bonus_rejects_negative_values() -> None:
    with pytest.raises(ValidationError):
        AiTuning.model_validate({"uprising_bonus": -1})


def test_max_armies_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        AiTuning.model_validate({"max_armies": 0})


def test_oath_tuning_defaults_and_bounds() -> None:
    tuning = AiTuning()

    assert (tuning.oath_honor_threshold, tuning.oath_break_penalty) == (2, 40)
    with pytest.raises(ValidationError):
        AiTuning.model_validate({"oath_break_penalty": -1})
