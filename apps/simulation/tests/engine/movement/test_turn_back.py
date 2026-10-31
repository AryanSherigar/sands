import itertools

from app.engine.movement import events
from app.models.world_army import MarchState
from strategy_contracts.enums import RelationStatus, Terrain

from tests.engine.movement.builders import (
    FACTION_A,
    FACTION_B,
    halt_order,
    kinds,
    make_army,
    make_map,
    make_scenario,
    make_world_for,
    move_order,
    play_turns,
    run_movement,
)

CHAIN = ["reg_a", "reg_b", "reg_c", "reg_d"]
SIDE = "reg_z"
LINKS = [*itertools.pairwise(CHAIN), ("reg_a", SIDE)]
WAR = {(FACTION_A, FACTION_B): RelationStatus.WAR}


def _scenario(terrain: Terrain = Terrain.MOUNTAIN, **tuning):
    terrains = {name: terrain for name in (*CHAIN, SIDE)}
    return make_scenario(make_map(terrains, LINKS), **tuning)


def _world(extra_armies=(), statuses=None):
    owners = {name: FACTION_A for name in (*CHAIN, SIDE)}
    armies = [make_army("army_a", FACTION_A, "reg_a"), *extra_armies]
    return make_world_for(owners, armies, statuses)


def _on_the_road(turns: int = 1):
    """army_a marching reg_a -> reg_b on mountains, `turns` turns in (100 points each)."""
    world, _ = play_turns(
        _world(), _scenario(), turns, [move_order("o1", "army_a", "reg_b")]
    )
    return world


def _army(world):
    return world.armies["army_a"]


def test_ordering_a_mid_road_army_to_its_origin_turns_it_around() -> None:
    result = run_movement(
        _on_the_road(), _scenario(), [move_order("o2", "army_a", "reg_a")]
    )
    assert events.ARMY_TURNED_BACK in kinds(result.events)
    assert "movement_order_rejected" not in kinds(result.events)


def test_the_turn_around_is_recorded_before_any_walking() -> None:
    world = _on_the_road(2)
    march = _army(world).march
    assert march.leg_progress == 200
    scenario = _scenario(budget_per_turn=1)
    result = run_movement(world, scenario, [move_order("o2", "army_a", "reg_a")])
    march = _army(result.world).march
    assert march.is_returning is True
    assert (march.from_id, march.to_id, march.route) == ("reg_a", "reg_b", [])
    assert march.leg_progress == 199
    assert _army(result.world).order.target_id == "reg_a"


def test_walking_back_covers_exactly_the_distance_already_walked() -> None:
    world = _on_the_road(1)
    back, _ = play_turns(world, _scenario(), 1, [move_order("o2", "army_a", "reg_a")])
    assert _army(back).location_id == "reg_a"
    assert _army(back).march is None
    assert _army(back).order is None


def test_a_longer_way_out_takes_proportionally_longer_to_walk_back() -> None:
    world = _on_the_road(2)
    midway, played = play_turns(
        world, _scenario(), 1, [move_order("o2", "army_a", "reg_a")]
    )
    assert _army(midway).march.leg_progress == 100
    assert _army(midway).march.is_returning is True
    assert events.ARMY_RETURNING in kinds(played)
    home, played = play_turns(midway, _scenario(), 1)
    assert _army(home).march is None
    assert events.ARMY_RETURNED in kinds(played)


def test_spare_budget_after_getting_home_starts_the_next_leg() -> None:
    world = _on_the_road(1)
    scenario = _scenario(Terrain.PLAIN, budget_per_turn=150)
    result = run_movement(world, scenario, [move_order("o2", "army_a", "reg_z")])
    army = _army(result.world)
    assert army.location_id == "reg_a"
    assert (army.march.to_id, army.march.leg_progress) == ("reg_z", 50)
    assert army.march.is_returning is False


def test_a_destination_only_reachable_through_the_origin_is_now_allowed() -> None:
    result = run_movement(
        _on_the_road(), _scenario(budget_per_turn=1), [move_order("o2", "army_a", SIDE)]
    )
    march = _army(result.world).march
    assert (march.is_returning, march.route) == (True, [SIDE])
    assert "movement_order_rejected" not in kinds(result.events)


def test_the_army_goes_forward_when_that_is_cheaper_than_walking_back() -> None:
    world = _on_the_road(2)
    result = run_movement(
        world, _scenario(budget_per_turn=1), [move_order("o2", "army_a", "reg_c")]
    )
    march = _army(result.world).march
    assert march.is_returning is False
    assert (march.to_id, march.route) == ("reg_b", ["reg_c"])


def test_the_army_walks_back_when_that_is_cheaper_than_going_on() -> None:
    world = _on_the_road(1)
    result = run_movement(
        world, _scenario(budget_per_turn=1), [move_order("o2", "army_a", SIDE)]
    )
    march = _army(result.world).march
    assert march.is_returning is True
    assert march.route == [SIDE]


def test_ordering_the_far_end_still_just_continues_the_leg() -> None:
    world = _on_the_road(1)
    result = run_movement(
        world, _scenario(budget_per_turn=1), [move_order("o2", "army_a", "reg_b")]
    )
    march = _army(result.world).march
    assert (march.is_returning, march.to_id, march.leg_progress) == (
        False,
        "reg_b",
        101,
    )


def test_a_halted_army_can_also_turn_back() -> None:
    world = _on_the_road(2)
    halted = run_movement(
        world, _scenario(budget_per_turn=1), [halt_order("o2", "army_a")]
    ).world
    assert _army(halted).march.is_halted is True
    result = run_movement(
        halted, _scenario(budget_per_turn=1), [move_order("o3", "army_a", "reg_a")]
    )
    assert _army(result.world).march.is_returning is True


def test_halting_a_returning_army_leaves_it_where_it_has_walked_to() -> None:
    world = _on_the_road(2)
    midway, _ = play_turns(world, _scenario(), 1, [move_order("o2", "army_a", "reg_a")])
    halted = run_movement(midway, _scenario(), [halt_order("o3", "army_a")]).world
    march = _army(halted).march
    assert (march.is_halted, march.is_returning, march.leg_progress) == (
        True,
        False,
        100,
    )
    resumed = run_movement(
        halted, _scenario(), [move_order("o4", "army_a", "reg_b")]
    ).world
    assert _army(resumed).march.leg_progress == 200


def test_a_returning_army_still_counts_as_standing_in_its_origin_region() -> None:
    enemy = make_army("army_0", FACTION_B, SIDE)
    world = _on_the_road(1)
    world.armies["army_0"] = enemy
    world.regions[SIDE].owner_id = FACTION_B
    world.relations = make_world_for({"reg_a": None}, [], WAR).relations
    orders = [
        move_order("o2", "army_a", "reg_a"),
        move_order("o3", "army_0", "reg_a", FACTION_B),
    ]
    result = run_movement(world, _scenario(budget_per_turn=300), orders)
    battle = result.world.pending_battles[0]
    assert battle.region_id == "reg_a"
    assert battle.defender_army_ids == ["army_a"]
    assert _army(result.world).march is None


def test_returning_and_advancing_armies_on_one_road_do_not_meet() -> None:
    enemy = make_army("army_b", FACTION_B, "reg_b")
    world = _on_the_road(1)
    world.armies["army_b"] = enemy
    world.relations = make_world_for({"reg_a": None}, [], WAR).relations
    orders = [
        move_order("o2", "army_a", "reg_a"),
        move_order("o3", "army_b", "reg_a", FACTION_B),
    ]
    result = run_movement(
        world, _scenario(Terrain.MOUNTAIN, budget_per_turn=60), orders
    )
    assert events.ROAD_MEETING not in kinds(result.events)
    assert result.world.pending_battles == []


def test_a_returning_march_is_valid_world_state() -> None:
    result = run_movement(
        _on_the_road(),
        _scenario(budget_per_turn=1),
        [move_order("o2", "army_a", "reg_a")],
    )
    army = _army(result.world)
    assert isinstance(army.march, MarchState)
    assert type(army).model_validate(army.model_dump()) == army
