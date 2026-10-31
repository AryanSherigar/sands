import pytest
from pydantic import ValidationError
from strategy_contracts.enums import PayLevel, TaxRate, TroopType
from strategy_contracts.scenario import EconomyTuning, StrategyScenario, Tuning


def test_defaults_cover_every_tax_rate_troop_type_and_pay_level() -> None:
    tuning = EconomyTuning()
    assert set(tuning.tax_rate_percent) == set(TaxRate)
    assert set(tuning.tax_unrest_drift) == set(TaxRate)
    assert set(tuning.upkeep_per_unit) == set(TroopType)
    assert set(tuning.pay_level_percent) == set(PayLevel)
    assert set(tuning.morale_recovery) == set(PayLevel)


def test_higher_tax_means_more_income_and_more_unrest_by_default() -> None:
    tuning = EconomyTuning()
    rates = [tuning.tax_rate_percent[rate] for rate in TaxRate]
    drift = [tuning.tax_unrest_drift[rate] for rate in TaxRate]
    assert rates == sorted(rates)
    assert drift == sorted(drift)


def test_heavier_troops_cost_more_to_keep_by_default() -> None:
    upkeep = EconomyTuning().upkeep_per_unit
    assert upkeep[TroopType.INFANTRY] < upkeep[TroopType.CAVALRY]
    assert upkeep[TroopType.CAVALRY] < upkeep[TroopType.ARCHERS_SIEGE]


def test_heavier_troops_cost_more_to_recruit_by_default() -> None:
    recruit = EconomyTuning().recruit_cost_per_unit
    assert recruit[TroopType.INFANTRY] < recruit[TroopType.CAVALRY]
    assert recruit[TroopType.CAVALRY] < recruit[TroopType.ARCHERS_SIEGE]


def test_recruit_costs_missing_a_troop_type_are_refused() -> None:
    with pytest.raises(ValidationError):
        EconomyTuning(recruit_cost_per_unit={TroopType.INFANTRY: 25})


def test_reduced_pay_is_cheaper_and_recovers_less_morale() -> None:
    tuning = EconomyTuning()
    assert tuning.pay_level_percent[PayLevel.REDUCED] < 100
    assert (
        tuning.morale_recovery[PayLevel.REDUCED] < tuning.morale_recovery[PayLevel.FULL]
    )


def test_tax_table_missing_a_rate_is_refused() -> None:
    with pytest.raises(ValidationError):
        EconomyTuning(tax_rate_percent={TaxRate.NORMAL: 100})


def test_upkeep_missing_a_troop_type_is_refused() -> None:
    with pytest.raises(ValidationError):
        EconomyTuning(upkeep_per_unit={TroopType.INFANTRY: 4})


def test_negative_upkeep_is_refused() -> None:
    upkeep = EconomyTuning().upkeep_per_unit | {TroopType.INFANTRY: -1}
    with pytest.raises(ValidationError):
        EconomyTuning(upkeep_per_unit=upkeep)


def test_pay_table_missing_a_level_is_refused() -> None:
    with pytest.raises(ValidationError):
        EconomyTuning(pay_level_percent={PayLevel.FULL: 100})


@pytest.mark.parametrize(
    "field",
    [
        "upkeep_troop_unit",
        "desertion_after_unpaid_turns",
        "loan_term_turns",
        "loan_installment_percent",
        "loan_refused_strikes",
        "credit_recovery_turns",
    ],
)
def test_zero_is_refused_where_it_would_divide_or_stall(field: str) -> None:
    with pytest.raises(ValidationError):
        EconomyTuning(**{field: 0})


@pytest.mark.parametrize(
    "field",
    [
        "desertion_percent",
        "raised_army_morale",
        "disband_return_percent",
        "manpower_cap_percent",
        "loan_base_interest_percent",
        "default_reputation_penalty",
    ],
)
def test_percent_fields_above_100_are_refused(field: str) -> None:
    with pytest.raises(ValidationError):
        EconomyTuning(**{field: 101})


def test_scenarios_without_an_economy_block_get_the_defaults() -> None:
    scenario = StrategyScenario.model_validate({"tuning": {}})
    assert scenario.tuning.economy == EconomyTuning()
    assert Tuning().economy == EconomyTuning()
