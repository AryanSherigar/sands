from app.engine.movement.costs import months_of_turn
from app.engine.rng import derive_rng
from app.models.world_state import WorldState
from strategy_contracts.battle import Weather, WeatherSeason
from strategy_contracts.scenario import StrategyScenario


def weather_for(
    world: WorldState, region_id: str, scenario: StrategyScenario
) -> Weather:
    """A local campaign observation uses its own key, independent of battle identity."""
    month = months_of_turn(world.clock)[0]
    movement = scenario.tuning.movement
    season = WeatherSeason.OTHER
    if month in movement.winter_months:
        season = WeatherSeason.WINTER
    elif month in movement.spring_months:
        season = WeatherSeason.SPRING
    weights = scenario.tuning.battle.weather_weights[season]
    rng = derive_rng(
        world.rng.seed, world.clock.turn, "battle_weather", region_id, season.value
    )
    return rng.weighted_choice(
        tuple(Weather), (weights.clear, weights.rain, weights.severe)
    )


def refresh_conditions(
    world: WorldState, battle_id: str, scenario: StrategyScenario
) -> None:
    from app.engine.battles.supply import supply_state

    battle = next(battle for battle in world.battles if battle.id == battle_id)
    battle.weather = weather_for(world, battle.region_id, scenario)
    battle.weather_turn = world.clock.turn
    for faction_id in sorted(battle.contingents):
        battle.contingents[faction_id].supply = supply_state(
            world, battle.region_id, faction_id, scenario
        )
