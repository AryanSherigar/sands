import pytest
from pydantic import ValidationError
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.pressure import PressureTuning, ShockKind
from strategy_contracts.scenario import Tuning


def test_defaults_validate() -> None:
    tuning = Tuning().pressure

    assert tuning.rule_version == "pressure-v1"
    assert len(tuning.band_thresholds) == 4
    assert tuning.devastation_step == 10
    assert tuning.hope_cancel_turns == 3
    assert tuning.relief_army_min_morale == 50


def test_band_thresholds_must_increase() -> None:
    with pytest.raises(ValidationError):
        PressureTuning(band_thresholds=[40, 20, 60, 80])


def test_every_shock_kind_has_an_amount() -> None:
    with pytest.raises(ValidationError):
        PressureTuning(shock_amounts={ShockKind.CAPITAL_FALLS: 10})

    assert set(PressureTuning().shock_amounts) == set(ShockKind)


def test_three_crowns_loads_with_default_pressure_tuning() -> None:
    scenario = load_three_crowns()

    assert scenario.tuning.pressure == PressureTuning()


def test_subsidy_limits_default_and_floor() -> None:
    tuning = Tuning().pressure

    assert tuning.subsidy_max_per_turn == 100
    assert tuning.subsidy_max_turns == 8
    for field in ("subsidy_max_per_turn", "subsidy_max_turns"):
        with pytest.raises(ValidationError):
            PressureTuning(**{field: 0})
