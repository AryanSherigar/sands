from app.engine.ending_rules.regime_fall import (
    is_regime_fall_pressure,
    is_regime_fallen,
)
from app.engine.ending_rules.streaks import advance_ending_streaks

from tests.engine.ending_rules.builders import (
    PLAYER,
    add_war,
    make_world,
    scenario_with,
    set_war_deficit,
)

PRESSURED = {
    "regime_fall_war_score_deficit": 10,
    "regime_fall_will_ceiling": 100,
    "regime_fall_stability_ceiling": 50,
    "regime_fall_streak_turns": 2,
}


def _pressured_world():
    world = make_world()
    set_war_deficit(add_war(world), 10)
    world.factions[PLAYER].stability = 10
    return world


def test_regime_fall_requires_all_three_conditions() -> None:
    scenario = scenario_with(**PRESSURED)
    assert is_regime_fall_pressure(_pressured_world(), scenario)

    calm = _pressured_world()
    calm.factions[PLAYER].stability = 90
    assert not is_regime_fall_pressure(calm, scenario)

    winning = _pressured_world()
    set_war_deficit(winning.wars[0], 0)
    assert not is_regime_fall_pressure(winning, scenario)

    willing = _pressured_world()
    strict = scenario_with(**{**PRESSURED, "regime_fall_will_ceiling": 0})
    assert not is_regime_fall_pressure(willing, strict)


def test_single_bad_turn_resets_streak() -> None:
    scenario = scenario_with(**PRESSURED)
    world = _pressured_world()
    advance_ending_streaks(world, scenario)
    assert world.endings.regime_fall_turns == 1
    world.factions[PLAYER].stability = 90
    advance_ending_streaks(world, scenario)
    assert world.endings.regime_fall_turns == 0
    assert not is_regime_fallen(world, scenario)


def test_regime_falls_once_streak_is_long_enough() -> None:
    scenario = scenario_with(**PRESSURED)
    world = _pressured_world()
    advance_ending_streaks(world, scenario)
    assert not is_regime_fallen(world, scenario)
    advance_ending_streaks(world, scenario)
    assert is_regime_fallen(world, scenario)
