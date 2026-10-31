from strategy_contracts.battle import Weather, WeatherSeason, WeatherWeights

from tests.engine.battles.builders import REGION, battle_fixture, exchange, start_battle


def test_weather_key_is_region_and_campaign_turn_and_does_not_consume_world_rng() -> (
    None
):
    from app.engine.battles.weather import weather_for

    world, scenario = battle_fixture()
    before = world.model_dump()
    values = [weather_for(world, REGION, scenario) for _ in range(4)]
    assert len(set(values)) == 1
    assert world.model_dump() == before
    start_battle(world, scenario)
    result = exchange(world, scenario)
    assert result.delta.battle.weather == values[0]
    assert result.delta.battle.weather_turn == 0


def test_weather_uses_calendar_seasons_and_tunable_weights() -> None:
    from app.engine.battles.weather import weather_for

    world, scenario = battle_fixture()
    scenario.tuning.battle.weather_weights[WeatherSeason.WINTER] = WeatherWeights(
        clear=0, rain=0, severe=100
    )
    scenario.tuning.battle.weather_weights[WeatherSeason.SPRING] = WeatherWeights(
        clear=0, rain=100, severe=0
    )
    world.clock.start_month = 12
    assert weather_for(world, REGION, scenario) == Weather.SEVERE
    world.clock.start_month = 3
    assert weather_for(world, REGION, scenario) == Weather.RAIN
