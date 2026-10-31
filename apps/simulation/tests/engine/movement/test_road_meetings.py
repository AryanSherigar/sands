import pytest
from app.engine.movement import events
from strategy_contracts.enums import RelationStatus, Terrain

from tests.engine.movement.builders import (
    FACTION_A,
    FACTION_B,
    kinds,
    make_army,
    make_map,
    make_scenario,
    make_world_for,
    move_order,
    play_turns,
)

WAR = {(FACTION_A, FACTION_B): RelationStatus.WAR}
PEACE = {(FACTION_A, FACTION_B): RelationStatus.PEACE}


def _head_on(terrain: Terrain, statuses, same_direction: bool = False):
    terrains = {"reg_a": terrain, "reg_b": terrain, "reg_c": terrain}
    scenario = make_scenario(
        make_map(terrains, [("reg_a", "reg_b"), ("reg_b", "reg_c")])
    )
    second_start = "reg_a" if same_direction else "reg_b"
    second_goal = "reg_b" if same_direction else "reg_a"
    world = make_world_for(
        {"reg_a": FACTION_A, "reg_b": FACTION_B, "reg_c": None},
        [
            make_army("army_a", FACTION_A, "reg_a"),
            make_army("army_b", FACTION_B, second_start),
        ],
        statuses,
    )
    orders = [
        move_order("o1", "army_a", "reg_b"),
        move_order("o2", "army_b", second_goal, FACTION_B),
    ]
    return world, scenario, orders


def test_armies_meeting_on_the_road_at_war_fight_where_the_lower_id_left() -> None:
    world, scenario, orders = _head_on(Terrain.HILLS, WAR)
    final, played = play_turns(world, scenario, 1, orders)
    assert events.ROAD_MEETING in kinds(played)
    battle = final.pending_battles[0]
    assert battle.region_id == "reg_a"
    assert battle.attacker_army_ids == ["army_a"]
    assert battle.defender_army_ids == ["army_b"]
    assert final.armies["army_b"].location_id == "reg_a"
    assert final.armies["army_a"].march is None
    assert final.armies["army_b"].march is None


def test_armies_still_apart_keep_marching() -> None:
    world, scenario, orders = _head_on(Terrain.MOUNTAIN, WAR)
    final, played = play_turns(world, scenario, 1, orders)
    assert events.ROAD_MEETING not in kinds(played)
    assert final.pending_battles == []
    assert final.armies["army_a"].march.leg_progress == 100


def test_they_meet_once_their_combined_progress_covers_the_road() -> None:
    world, scenario, orders = _head_on(Terrain.MOUNTAIN, WAR)
    final, played = play_turns(world, scenario, 2, orders)
    assert events.ROAD_MEETING in kinds(played)
    assert len(final.pending_battles) == 1


def test_armies_at_peace_pass_each_other_on_the_road() -> None:
    world, scenario, orders = _head_on(Terrain.HILLS, PEACE)
    final, played = play_turns(world, scenario, 1, orders)
    assert events.ROAD_MEETING not in kinds(played)
    assert final.pending_battles == []


def test_armies_walking_the_same_way_never_meet_on_the_road() -> None:
    world, scenario, orders = _head_on(Terrain.HILLS, WAR, same_direction=True)
    final, played = play_turns(world, scenario, 1, orders)
    assert events.ROAD_MEETING not in kinds(played)
    assert final.pending_battles == []


@pytest.mark.parametrize("turns", [1, 2, 3])
def test_road_meetings_are_deterministic(turns: int) -> None:
    world, scenario, orders = _head_on(Terrain.HILLS, WAR)
    first, _ = play_turns(world, scenario, turns, orders)
    second, _ = play_turns(world, scenario, turns, orders)
    assert first.model_dump() == second.model_dump()


def test_armies_whose_progress_exactly_covers_the_road_meet() -> None:
    terrains = {"reg_a": Terrain.HILLS, "reg_b": Terrain.HILLS}
    scenario = make_scenario(
        make_map(terrains, [("reg_a", "reg_b")]), budget_per_turn=75
    )
    world = make_world_for(
        {"reg_a": FACTION_A, "reg_b": FACTION_B},
        [
            make_army("army_a", FACTION_A, "reg_a"),
            make_army("army_b", FACTION_B, "reg_b"),
        ],
        WAR,
    )
    orders = [
        move_order("o1", "army_a", "reg_b"),
        move_order("o2", "army_b", "reg_a", FACTION_B),
    ]
    final, played = play_turns(world, scenario, 1, orders)
    assert events.ROAD_MEETING in kinds(played)
    assert len(final.pending_battles) == 1


def test_armies_one_point_short_of_covering_the_road_do_not_meet() -> None:
    terrains = {"reg_a": Terrain.HILLS, "reg_b": Terrain.HILLS}
    scenario = make_scenario(
        make_map(terrains, [("reg_a", "reg_b")]), budget_per_turn=74
    )
    world = make_world_for(
        {"reg_a": FACTION_A, "reg_b": FACTION_B},
        [
            make_army("army_a", FACTION_A, "reg_a"),
            make_army("army_b", FACTION_B, "reg_b"),
        ],
        WAR,
    )
    orders = [
        move_order("o1", "army_a", "reg_b"),
        move_order("o2", "army_b", "reg_a", FACTION_B),
    ]
    _, played = play_turns(world, scenario, 1, orders)
    assert events.ROAD_MEETING not in kinds(played)
