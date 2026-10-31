from app.engine.movement import events
from app.engine.movement.contact import ContactKind, classify_entry
from app.engine.movement.knowledge import known_hazards
from app.engine.movement.map_index import build_map_index
from app.models.world_diplomacy import CommitmentState
from strategy_contracts.enums import RelationStatus, Terrain
from strategy_contracts.terms import MilitaryAccessTerm

from tests.engine.movement.builders import (
    FACTION_A,
    FACTION_B,
    make_army,
    make_map,
    make_scenario,
    make_world_for,
    move_order,
    run_movement,
)

TURNS = 6
GAME_MAP = make_map(
    {"reg_a": Terrain.PLAIN, "reg_b": Terrain.PLAIN},
    [("reg_a", "reg_b")],
)
SCENARIO = make_scenario(GAME_MAP)
PEACE = {(FACTION_A, FACTION_B): RelationStatus.PEACE}
WAR = {(FACTION_A, FACTION_B): RelationStatus.WAR}


def _world(statuses, ruleset: int = 1, grantee: str = FACTION_A):
    army = make_army("army_a", FACTION_A, "reg_a")
    world = make_world_for({"reg_a": FACTION_A, "reg_b": FACTION_B}, [army], statuses)
    world.treaty_ruleset = ruleset
    term = MilitaryAccessTerm(
        grantor_id=FACTION_B if grantee == FACTION_A else FACTION_A,
        grantee_id=grantee,
        duration_turns=TURNS,
    )
    world.commitments.append(
        CommitmentState(
            id="commitment_1",
            term=term,
            start_turn=world.clock.turn,
            end_turn=world.clock.turn + TURNS,
        )
    )
    return world


def _entry(world):
    return classify_entry(world, world.armies["army_a"], "reg_b").kind


def test_a_grantee_walks_into_the_grantors_land_without_confrontation() -> None:
    assert _entry(_world(PEACE)) is ContactKind.NONE


def test_the_grant_only_runs_one_way() -> None:
    assert _entry(_world(PEACE, grantee=FACTION_B)) is ContactKind.CONFRONTATION


def test_access_is_ignored_below_the_treaty_ruleset() -> None:
    assert _entry(_world(PEACE, ruleset=0)) is ContactKind.CONFRONTATION


def test_war_voids_the_grant() -> None:
    assert _entry(_world(WAR)) is ContactKind.ENEMY_REGION


def test_an_expired_grant_confronts_again() -> None:
    world = _world(PEACE)
    world.commitments[0].end_turn = world.clock.turn

    assert _entry(world) is ContactKind.CONFRONTATION


def test_granted_land_is_not_a_known_hazard() -> None:
    world = _world(PEACE)
    index = build_map_index(SCENARIO.map)

    assert "reg_b" not in known_hazards(world, FACTION_A, index)


def test_a_march_under_access_arrives_instead_of_stopping_at_the_border() -> None:
    world = _world(PEACE)

    result = run_movement(world, SCENARIO, [move_order("o1", "army_a", "reg_b")])

    assert events.ARMY_ARRIVED in [event.kind for event in result.events]
    assert events.BORDER_CONFRONTATION not in [event.kind for event in result.events]
