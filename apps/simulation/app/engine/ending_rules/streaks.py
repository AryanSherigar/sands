from app.engine.ending_rules.hegemony import is_hegemonic_position
from app.engine.ending_rules.regime_fall import is_regime_fall_pressure
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def _next_streak(current: int, is_holding: bool) -> int:
    return current + 1 if is_holding else 0


def advance_ending_streaks(world: WorldState, scenario: StrategyScenario) -> None:
    state = world.endings
    state.regime_fall_turns = _next_streak(
        state.regime_fall_turns, is_regime_fall_pressure(world, scenario)
    )
    state.hegemony_turns = _next_streak(
        state.hegemony_turns, is_hegemonic_position(world, scenario)
    )
    if world.wars:
        state.has_seen_war = True
