from app.engine.negotiation import player_faction_id
from app.engine.pressure.wars import side_of, wars_of
from app.engine.pressure.will import compute_will
from app.models.world_diplomacy import WarSide, WarState
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def _score_deficit(war: WarState, side: WarSide | None) -> int:
    if side == WarSide.ATTACKER:
        return war.war_score_defender - war.war_score_attacker
    return war.war_score_attacker - war.war_score_defender


def worst_war_deficit(world: WorldState) -> int:
    player_id = player_faction_id(world)
    deficits = [
        _score_deficit(war, side_of(war, player_id))
        for war in wars_of(world, player_id)
    ]
    return max(deficits, default=0)


def is_regime_fall_pressure(world: WorldState, scenario: StrategyScenario) -> bool:
    tuning = scenario.tuning.endings
    player_id = player_faction_id(world)
    if not wars_of(world, player_id):
        return False
    is_losing = worst_war_deficit(world) >= tuning.regime_fall_war_score_deficit
    is_broken = (
        compute_will(world, scenario, player_id).value
        <= tuning.regime_fall_will_ceiling
    )
    is_unstable = (
        world.factions[player_id].stability < tuning.regime_fall_stability_ceiling
    )
    return is_losing and is_broken and is_unstable


def is_regime_fallen(world: WorldState, scenario: StrategyScenario) -> bool:
    streak = scenario.tuning.endings.regime_fall_streak_turns
    return world.endings.regime_fall_turns >= streak
