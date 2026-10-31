from app.models.world_state import WorldState
from strategy_contracts.overtures import OvertureTuning
from strategy_contracts.scenario import StrategyScenario

from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    set_score,
)
from tests.engine.peace.builders import make_world as make_peace_world
from tests.engine.vassals.builders import set_axes

__all__ = [
    "CAUTIOUS_RIVAL",
    "PLAYER",
    "SCENARIO",
    "WRATHFUL_RIVAL",
    "add_war",
    "make_world",
    "scenario_with",
    "set_axes",
    "set_score",
    "war_world",
]


def make_world() -> WorldState:
    world = make_peace_world()
    world.succession_ruleset = 0
    return world


def scenario_with(**overture_fields: int) -> StrategyScenario:
    tuning = SCENARIO.tuning.model_copy(
        update={"overtures": OvertureTuning(**overture_fields)}
    )
    return SCENARIO.model_copy(update={"tuning": tuning})


def war_world(attacker_score: int = 0, defender_score: int = 0) -> WorldState:
    world = make_world()
    set_score(add_war(world), attacker_score, defender_score)
    return world
