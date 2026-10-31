from app.models.world_character import LeaderState
from app.models.world_state import CURRENT_SUCCESSION_RULESET, WorldState
from strategy_contracts.scenario import StrategyScenario

from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

__all__ = [
    "CAUTIOUS_RIVAL",
    "PLAYER",
    "SCENARIO",
    "WRATHFUL_RIVAL",
    "add_war",
    "leader_of",
    "make_succession_world",
    "make_world",
    "tuned",
]


def make_succession_world(player_faction_id: str = PLAYER) -> WorldState:
    world = make_world(player_faction_id)
    world.succession_ruleset = CURRENT_SUCCESSION_RULESET
    return world


def leader_of(world: WorldState, faction_id: str) -> LeaderState:
    leader_id = world.factions[faction_id].leader_id
    assert leader_id is not None
    return world.leaders[leader_id]


def tuned(scenario: StrategyScenario, **updates: object) -> StrategyScenario:
    copy = scenario.model_copy(deep=True)
    copy.tuning.succession = copy.tuning.succession.model_copy(update=updates)
    return copy
