import pytest
from pydantic import ValidationError
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import (
    BUILTIN_STANCES,
    MAX_STANCE_SHIFT,
    MIN_STANCE_SHIFT,
    ScoreCategory,
    StanceDefinition,
)


def _stance(shifts: dict[str, int]) -> dict[str, object]:
    return {"id": "reclaim_marches", "name": "Reclaim", "shifts": shifts}


def test_shift_above_max_is_rejected() -> None:
    with pytest.raises(ValidationError):
        StanceDefinition.model_validate(_stance({"attack": MAX_STANCE_SHIFT + 1}))


def test_shift_below_min_is_rejected() -> None:
    with pytest.raises(ValidationError):
        StanceDefinition.model_validate(_stance({"hoard": MIN_STANCE_SHIFT - 1}))


def test_unknown_category_is_rejected() -> None:
    with pytest.raises(ValidationError):
        StanceDefinition.model_validate(_stance({"conquer": 1}))


def test_builtin_ids_are_unique_and_in_bounds() -> None:
    ids = [stance.id for stance in BUILTIN_STANCES]
    assert len(ids) == len(set(ids))
    assert {"rebuild", "court_ally", "revenge_on_player", "expand", "turtle"} <= set(
        ids
    )
    for stance in BUILTIN_STANCES:
        assert set(stance.shifts) <= set(ScoreCategory)
        assert all(
            MIN_STANCE_SHIFT <= value <= MAX_STANCE_SHIFT
            for value in stance.shifts.values()
        )


def test_scenario_defaults_to_no_custom_stances() -> None:
    scenario = StrategyScenario()
    assert scenario.custom_stances == []


def test_scenario_accepts_custom_stance_and_faction_menu() -> None:
    scenario = StrategyScenario.model_validate(
        {
            "custom_stances": [_stance({"attack": 2, "build": -1})],
            "factions": [
                {
                    "id": "ashford",
                    "name": "Ashford",
                    "color": "#aabbcc",
                    "stance_ids": ["reclaim_marches", "turtle"],
                }
            ],
        }
    )
    assert scenario.custom_stances[0].shifts[ScoreCategory.ATTACK] == 2
    assert scenario.factions[0].stance_ids == ["reclaim_marches", "turtle"]
