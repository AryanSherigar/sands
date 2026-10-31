from app.engine.stances.cadence import (
    STANCE_INTERVAL_TURNS,
    leaders_due_for_stance,
    major_event_leaders,
)
from app.models.world_character import LeaderState
from app.models.world_diplomacy import RelationState
from app.models.world_faction import StanceState
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus

from tests.models.builders import make_world

AI_FACTION = "house_ashford"
PLAYER_FACTION = "house_carrow"


def _world() -> WorldState:
    world = make_world()
    world.leaders = {
        "mira": LeaderState(id="mira", name="Mira", faction_id=AI_FACTION, age=40),
        "valdren": LeaderState(
            id="valdren", name="Valdren", faction_id=PLAYER_FACTION, age=40
        ),
    }
    world.factions[AI_FACTION].leader_id = "mira"
    world.factions[PLAYER_FACTION].leader_id = "valdren"
    return world


def test_unstanced_ai_leader_is_due() -> None:
    assert leaders_due_for_stance(_world(), 1) == ["mira"]


def test_leader_is_due_after_six_turns() -> None:
    world = _world()
    world.factions[AI_FACTION].stance = StanceState(option_id="turtle", chosen_turn=2)
    assert STANCE_INTERVAL_TURNS == 6
    assert leaders_due_for_stance(world, 7) == []
    assert leaders_due_for_stance(world, 8) == ["mira"]


def test_player_dead_and_leaderless_factions_are_never_due() -> None:
    world = _world()
    world.leaders["mira"].is_alive = False
    assert leaders_due_for_stance(world, 1) == []
    world.leaders["mira"].is_alive = True
    world.factions[AI_FACTION].leader_id = None
    assert leaders_due_for_stance(world, 1) == []
    world.factions[AI_FACTION].leader_id = "mira"
    world.factions[AI_FACTION].is_destroyed = True
    assert leaders_due_for_stance(world, 1) == []


def test_pending_request_for_same_turn_is_not_due_again() -> None:
    world = _world()
    world.factions[AI_FACTION].stance = StanceState(requested_for_turn=1)
    assert leaders_due_for_stance(world, 1) == []
    assert leaders_due_for_stance(world, 2) == ["mira"]


def test_capital_loss_is_a_major_event() -> None:
    before = _world()
    before.factions[AI_FACTION].capital_region_id = "ashford"
    after = before.model_copy(deep=True)
    after.regions["ashford"].owner_id = PLAYER_FACTION
    assert major_event_leaders(before, after) == ["mira"]


def test_leader_replacement_is_a_major_event() -> None:
    before = _world()
    after = before.model_copy(deep=True)
    after.leaders["heir"] = LeaderState(
        id="heir", name="Heir", faction_id=AI_FACTION, age=20
    )
    after.factions[AI_FACTION].leader_id = "heir"
    assert major_event_leaders(before, after) == ["heir"]


def test_new_war_is_a_major_event_for_both_ai_sides() -> None:
    before = _world()
    before.factions["house_third"] = before.factions[AI_FACTION].model_copy(
        update={"id": "house_third", "leader_id": "third"}
    )
    before.leaders["third"] = LeaderState(
        id="third", name="Third", faction_id="house_third", age=50
    )
    after = before.model_copy(deep=True)
    after.relations.append(
        RelationState(
            faction_a=AI_FACTION,
            faction_b="house_third",
            status=RelationStatus.WAR,
            since_turn=3,
        )
    )
    assert major_event_leaders(before, after) == ["mira", "third"]


def test_quiet_turn_has_no_major_events() -> None:
    before = _world()
    assert major_event_leaders(before, before.model_copy(deep=True)) == []
