from app.models.world_character import (
    LeaderState,
    MemoryState,
    OpinionReason,
    OpinionState,
)
from app.models.world_state import WorldState
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.letters import LetterTuning
from strategy_contracts.scenario import StrategyScenario

from tests.models.builders import make_world

PLAYER = "house_carrow"
RIVAL = "house_ashford"
PLAYER_LEADER = "valdren"
RIVAL_LEADER = "mira"
TURN = 4


def letter_world(turn: int = TURN, is_remembered: bool = True) -> WorldState:
    world = make_world()
    world.clock.turn = turn
    world.leaders = {
        PLAYER_LEADER: LeaderState(
            id=PLAYER_LEADER, name="Valdren", faction_id=PLAYER, age=40
        ),
        RIVAL_LEADER: LeaderState(
            id=RIVAL_LEADER, name="Mira", faction_id=RIVAL, age=40
        ),
    }
    world.factions[PLAYER].leader_id = PLAYER_LEADER
    world.factions[RIVAL].leader_id = RIVAL_LEADER
    if is_remembered:
        remember_player(world)
    return world


def remember_player(world: WorldState) -> None:
    world.leaders[RIVAL_LEADER].memories.append(
        MemoryState(kind="pact_signed", turn=1, subject_id=PLAYER_LEADER, weight=12)
    )


def set_opinion(world: WorldState, value: int) -> None:
    world.leaders[RIVAL_LEADER].opinions[PLAYER_LEADER] = OpinionState(
        target_id=PLAYER_LEADER,
        reasons=[OpinionReason(cause="test", value=value, fade_per_turn=0)],
    )


def letter_scenario(is_enabled: bool = True) -> StrategyScenario:
    scenario = load_three_crowns()
    scenario.tuning.letters = LetterTuning(is_enabled=is_enabled)
    return scenario
