import pytest
from pydantic import ValidationError
from strategy_contracts.scenario import InternalTuning, Tuning


def test_internal_tuning_has_safe_defaults_in_every_scenario() -> None:
    tuning = Tuning().internal

    assert tuning == InternalTuning()
    assert tuning.revolt_unrest_threshold == 70
    assert tuning.uprising_supply_penalty_percent == 50


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("battle_loss_unit", 0),
        ("revolt_unrest_threshold", 101),
        ("uprising_cooldown_turns", -1),
    ],
)
def test_internal_tuning_rejects_invalid_bounds(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        InternalTuning(**{field: value})
