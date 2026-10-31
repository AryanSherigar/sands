from app.engine.diplomacy.grounds import grant_ground
from app.engine.succession.crisis import tick_crises
from app.engine.succession.heirs import regent_id_for
from app.engine.succession.install import kill_ruler
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.succession import HeirSetup

from tests.engine.succession.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    leader_of,
    make_succession_world,
)

TUNING = SCENARIO.tuning.succession
TURNS_PER_YEAR = 6


def _scenario_with_minor_heir(world: WorldState, faction_id: str, age: int):
    scenario = SCENARIO.model_copy(deep=True)
    leader_id = world.factions[faction_id].leader_id
    leader = next(item for item in scenario.leaders if item.id == leader_id)
    leader.heir = HeirSetup(
        id=f"heir_of_{faction_id}",
        name="Young Heir",
        trait_ids=["cruel", "proud"],
        ambition_ids=[leader.ambition_ids[0]],
        age=age,
        history="Kept safe in a tower.",
    )
    return scenario


def _advance(world: WorldState, turns: int) -> None:
    world.clock.turn += turns


def test_minor_heir_promoted_on_coming_of_age_turn() -> None:
    world = make_succession_world()
    scenario = _scenario_with_minor_heir(world, CAUTIOUS_RIVAL, age=15)
    kill_ruler(world, scenario, CAUTIOUS_RIVAL, "illness")
    _advance(world, TURNS_PER_YEAR - 1)

    assert tick_crises(world, scenario) == []
    assert leader_of(world, CAUTIOUS_RIVAL).id == regent_id_for(CAUTIOUS_RIVAL)

    _advance(world, 1)
    events = tick_crises(world, scenario)

    heir = leader_of(world, CAUTIOUS_RIVAL)
    assert heir.id == f"heir_of_{CAUTIOUS_RIVAL}"
    assert heir.age == TUNING.coming_of_age
    assert world.succession.crises == []
    assert [event.kind for event in events] == ["heir_came_of_age"]


def test_regent_promoted_when_crisis_ends() -> None:
    world = make_succession_world()
    kill_ruler(world, SCENARIO, CAUTIOUS_RIVAL, "illness")
    _advance(world, TUNING.crisis_turns - 1)
    assert tick_crises(world, SCENARIO) == []
    assert len(world.succession.crises) == 1

    _advance(world, 1)
    events = tick_crises(world, SCENARIO)

    assert world.succession.crises == []
    assert leader_of(world, CAUTIOUS_RIVAL).id == regent_id_for(CAUTIOUS_RIVAL)
    assert [event.kind for event in events] == ["crisis_ended"]


def test_dead_regent_replaced_and_timer_restarts() -> None:
    world = make_succession_world()
    kill_ruler(world, SCENARIO, CAUTIOUS_RIVAL, "illness")
    _advance(world, 3)

    kill_ruler(world, SCENARIO, CAUTIOUS_RIVAL, "illness")

    (crisis,) = world.succession.crises
    assert crisis.ends_turn == world.clock.turn + TUNING.crisis_turns
    assert leader_of(world, CAUTIOUS_RIVAL).is_alive is True


def test_dead_regent_keeps_the_pending_minor_heir() -> None:
    world = make_succession_world()
    scenario = _scenario_with_minor_heir(world, CAUTIOUS_RIVAL, age=10)
    kill_ruler(world, scenario, CAUTIOUS_RIVAL, "illness")
    _advance(world, 2)

    kill_ruler(world, scenario, CAUTIOUS_RIVAL, "illness")

    (crisis,) = world.succession.crises
    assert crisis.heir_id == f"heir_of_{CAUTIOUS_RIVAL}"
    assert crisis.is_penalty_active is False


def test_grounds_follow_the_heir_without_a_second_reduction() -> None:
    world = make_succession_world()
    scenario = _scenario_with_minor_heir(world, CAUTIOUS_RIVAL, age=15)
    kill_ruler(world, scenario, CAUTIOUS_RIVAL, "illness")
    regent_id = regent_id_for(CAUTIOUS_RIVAL)
    ground = grant_ground(
        world,
        scenario,
        kind=GroundKind.CLAIM,
        holder_faction_id=CAUTIOUS_RIVAL,
        target_faction_id=PLAYER,
        region_id=next(iter(world.regions)),
        strength=60,
    )
    assert ground.holder_leader_id == regent_id
    strength = ground.strength
    _advance(world, TURNS_PER_YEAR)

    tick_crises(world, scenario)

    assert ground.holder_leader_id == f"heir_of_{CAUTIOUS_RIVAL}"
    assert ground.strength == strength


def test_crisis_for_a_destroyed_faction_is_dropped_quietly() -> None:
    world = make_succession_world()
    kill_ruler(world, SCENARIO, CAUTIOUS_RIVAL, "illness")
    world.factions[CAUTIOUS_RIVAL].is_destroyed = True
    _advance(world, TUNING.crisis_turns)

    tick_crises(world, SCENARIO)

    assert world.succession.crises == []
