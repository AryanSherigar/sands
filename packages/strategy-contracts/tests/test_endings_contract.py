import pytest
from pydantic import ValidationError
from strategy_contracts.endings import EndingGrade, EndingsTuning
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scenario import Tuning


def test_defaults_weights_sum_to_100() -> None:
    tuning = EndingsTuning()
    total = (
        tuning.weight_position
        + tuning.weight_stability
        + tuning.weight_treasury
        + tuning.weight_will
        + tuning.weight_strain
    )
    assert total == 100


def test_rejects_weights_not_summing_to_100() -> None:
    with pytest.raises(ValidationError):
        EndingsTuning(weight_position=50)


def test_rejects_unsorted_thresholds() -> None:
    with pytest.raises(ValidationError):
        EndingsTuning(grade_thresholds=[60, 40, 80])


def test_rejects_wrong_threshold_count() -> None:
    with pytest.raises(ValidationError):
        EndingsTuning(grade_thresholds=[30, 60])


def test_vassal_best_grade_cannot_be_pyrrhic() -> None:
    with pytest.raises(ValidationError):
        EndingsTuning(vassal_best_grade=EndingGrade.PYRRHIC)


def test_tuning_mounts_and_defaults_for_legacy_scenario() -> None:
    assert Tuning().endings.toggles.is_hegemony_enabled is True
    assert load_three_crowns().tuning.endings == EndingsTuning()
