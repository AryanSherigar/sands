from app.engine.movement import events
from app.models.orders import MoveArmyOrder, QueuedOrder
from strategy_contracts.enums import RelationStatus, RouteStyle, Terrain

from tests.engine.movement.builders import (
    FACTION_A,
    FACTION_B,
    kinds,
    make_army,
    make_map,
    make_scenario,
    make_world_for,
    play_turns,
    run_movement,
)

NAMES = ["reg_s", "reg_h", "reg_a1", "reg_a2", "reg_g"]
LINKS = [
    ("reg_s", "reg_h"),
    ("reg_h", "reg_g"),
    ("reg_s", "reg_a1"),
    ("reg_a1", "reg_a2"),
    ("reg_a2", "reg_g"),
]
PEACE = {(FACTION_A, FACTION_B): RelationStatus.PEACE}


def _scenario(terrain: Terrain = Terrain.PLAIN, roads=(), **tuning):
    terrains = {name: terrain for name in NAMES}
    return make_scenario(make_map(terrains, LINKS, roads), **tuning)


def _world(foreign_hazard: bool = True):
    owners = dict.fromkeys(NAMES, FACTION_A)
    if foreign_hazard:
        owners["reg_h"] = FACTION_B
    return make_world_for(owners, [make_army("army_a", FACTION_A, "reg_s")], PEACE)


def _order(destination="reg_g", **choices) -> QueuedOrder:
    order = MoveArmyOrder(
        faction_id=FACTION_A, army_id="army_a", to_region_id=destination, **choices
    )
    return QueuedOrder(id="o1", order=order, cost=1, queued_turn=0)


def _march(world, scenario, order):
    result = run_movement(world, scenario, [order])
    return result, result.world.armies["army_a"].march


def _slow(**tuning):
    return _scenario(budget_per_turn=1, **tuning)


def test_the_default_order_takes_the_fastest_route_even_through_foreign_land() -> None:
    _, march = _march(_world(), _slow(), _order())
    assert (march.to_id, march.route) == ("reg_h", ["reg_g"])


def test_a_safest_order_goes_round_foreign_land() -> None:
    _, march = _march(_world(), _slow(), _order(route_style=RouteStyle.SAFEST))
    assert (march.to_id, march.route) == ("reg_a1", ["reg_a2", "reg_g"])


def test_safest_does_not_fear_land_it_cannot_see() -> None:
    owners = dict.fromkeys(NAMES, None)
    owners["reg_s"] = FACTION_A
    owners["reg_g"] = FACTION_B
    world = make_world_for(owners, [make_army("army_a", FACTION_A, "reg_s")], PEACE)
    _, march = _march(world, _slow(), _order(route_style=RouteStyle.SAFEST))
    assert march.to_id == "reg_h"


def test_a_safest_march_is_not_stopped_at_the_border_it_avoided() -> None:
    final, played = play_turns(
        _world(),
        _scenario(),
        4,
        [_order(route_style=RouteStyle.SAFEST)],
    )
    assert final.armies["army_a"].location_id == "reg_g"
    assert events.BORDER_CONFRONTATION not in kinds(played)


def test_the_same_march_with_the_default_style_is_stopped_at_the_border() -> None:
    final, played = play_turns(_world(), _scenario(), 4, [_order()])
    assert events.BORDER_CONFRONTATION in kinds(played)
    assert final.armies["army_a"].location_id == "reg_s"


def test_a_roads_order_takes_the_road_detour() -> None:
    roads = [("reg_s", "reg_a1"), ("reg_a1", "reg_a2"), ("reg_a2", "reg_g")]
    scenario = _scenario(roads=roads, budget_per_turn=1, roads_off_road_penalty=80)
    _, march = _march(_world(False), scenario, _order(route_style=RouteStyle.ROADS))
    assert march.to_id == "reg_a1"


def test_a_via_region_shapes_the_route() -> None:
    _, march = _march(_world(False), _slow(), _order(via_region_ids=["reg_a2"]))
    assert (march.to_id, march.route) == ("reg_a1", ["reg_a2", "reg_g"])


def test_an_avoided_region_is_not_entered() -> None:
    _, march = _march(_world(False), _slow(), _order(avoid_region_ids=["reg_h"]))
    assert march.to_id == "reg_a1"


def test_avoiding_the_destination_is_rejected_with_its_own_reason() -> None:
    result, march = _march(_world(), _slow(), _order(avoid_region_ids=["reg_g"]))
    assert march is None
    assert result.events[0].cause.summary_key.endswith("avoid_blocks_goal")


def test_avoiding_every_way_in_is_rejected_as_no_route() -> None:
    order = _order(avoid_region_ids=["reg_h", "reg_a1"])
    result, _ = _march(_world(), _slow(), order)
    assert result.events[0].cause.summary_key.endswith("no_route")


def test_a_via_that_cannot_be_reached_is_rejected() -> None:
    terrains = {**dict.fromkeys(NAMES, Terrain.PLAIN), "reg_x": Terrain.PLAIN}
    scenario = make_scenario(make_map(terrains, LINKS), budget_per_turn=1)
    owners = {**dict.fromkeys(NAMES, FACTION_A), "reg_x": FACTION_A}
    world = make_world_for(owners, [make_army("army_a", FACTION_A, "reg_s")])
    result, _ = _march(world, scenario, _order(via_region_ids=["reg_x"]))
    assert result.events[0].cause.summary_key.endswith("no_route")


def test_style_applies_when_an_army_on_the_road_picks_a_new_way() -> None:
    scenario = _scenario(Terrain.MOUNTAIN)
    moving, _ = play_turns(_world(), scenario, 1, [_order("reg_a1")])
    slow = _scenario(Terrain.MOUNTAIN, budget_per_turn=1)
    _, march = _march(moving, slow, _order("reg_g", route_style=RouteStyle.SAFEST))
    assert march.to_id == "reg_a1"
    assert march.route == ["reg_a2", "reg_g"]


def test_avoid_applies_when_an_army_on_the_road_picks_a_new_way() -> None:
    scenario = _scenario(Terrain.MOUNTAIN)
    moving, _ = play_turns(_world(False), scenario, 1, [_order("reg_a1")])
    slow = _scenario(Terrain.MOUNTAIN, budget_per_turn=1)
    _, march = _march(moving, slow, _order("reg_g", avoid_region_ids=["reg_a2"]))
    assert march is not None
    assert "reg_a2" not in [march.to_id, *march.route]


def test_a_march_planned_with_choices_is_still_a_valid_walk() -> None:
    final, _ = play_turns(
        _world(),
        _scenario(),
        8,
        [_order(route_style=RouteStyle.SAFEST, via_region_ids=["reg_a2"])],
    )
    assert final.armies["army_a"].location_id == "reg_g"
    assert final.armies["army_a"].march is None
