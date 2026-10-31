import pytest
from pydantic import ValidationError
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.siege import SiegeTuning


def test_default_siege_tuning_values() -> None:
    tuning = SiegeTuning()

    assert tuning.full_progress == 100
    assert tuning.troop_factor == 10
    assert tuning.garrison_floor == 100
    assert tuning.min_step == 5
    assert tuning.hold_delay == 3
    assert tuning.conquest_unrest == 20


def test_scenario_without_siege_block_validates() -> None:
    scenario = load_three_crowns()

    assert scenario.tuning.siege.hold_delay == 3


def test_hold_delay_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        SiegeTuning(hold_delay=0)


def test_conquest_unrest_is_a_percent() -> None:
    with pytest.raises(ValidationError):
        SiegeTuning(conquest_unrest=101)
