from app.models.world_diplomacy import TruceState, WarState
from app.models.world_state import WorldState
from strategy_contracts.endings import EndingsTuning
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
    "add_truce",
    "add_war",
    "make_world",
    "scenario_with",
]


def scenario_with(**updates: object) -> StrategyScenario:
    endings = EndingsTuning(**updates)
    tuning = SCENARIO.tuning.model_copy(update={"endings": endings})
    return SCENARIO.model_copy(update={"tuning": tuning})


def add_truce(
    world: WorldState,
    expires_in: int,
    guarantor_ids: list[str],
    rival_id: str = WRATHFUL_RIVAL,
) -> TruceState:
    truce = TruceState(
        id="truce_1",
        faction_a=PLAYER,
        faction_b=rival_id,
        signed_turn=world.clock.turn,
        expires_turn=world.clock.turn + expires_in,
        guarantor_ids=guarantor_ids,
        origin_war_id="war_1",
    )
    world.truces.append(truce)
    return truce


def set_war_deficit(war: WarState, deficit: int) -> None:
    war.war_score_attacker = deficit
    war.war_score_defender = 0
