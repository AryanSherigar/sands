import pytest
from pydantic import ValidationError
from strategy_contracts.scenario import StrategyScenario


def test_battle_defaults_cover_terrain_troops_and_weather() -> None:
    battle = StrategyScenario().tuning.battle
    assert battle.frontage["mountain"] == 300
    assert battle.troop_attack["cavalry"] == 14
    assert battle.weather_weights["winter"].severe == 30
    assert battle.max_exchanges_per_turn == 4


@pytest.mark.parametrize(
    "field,value",
    [
        ("frontage", {"plain": 1000}),
        ("troop_attack", {"infantry": 10, "cavalry": -1, "archers_siege": 12}),
        ("frontage", {"unknown": 1}),
        ("weather_weights", {"winter": {"clear": 40, "rain": 40, "severe": 40}}),
        ("professional_recon_rating", 101),
        (
            "formation_reserve_percent",
            {"balanced": 25, "defensive": 101, "concentrated": 10},
        ),
    ],
)
def test_invalid_battle_tuning_is_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        StrategyScenario.model_validate({"tuning": {"battle": {field: value}}})
