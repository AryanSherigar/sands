import itertools

import pytest
from app.engine.movement.costs import route_base_cost, route_total_cost
from app.engine.movement.map_index import build_map_index
from app.engine.movement.pathing import find_route
from app.engine.movement.route_options import RoutePreferences, plan_route
from strategy_contracts.enums import RouteStyle, Terrain
from strategy_contracts.scenario import MovementTuning

from tests.engine.movement.builders import make_map

TUNING = MovementTuning()
FASTEST = RoutePreferences()
SAFEST = RoutePreferences(style=RouteStyle.SAFEST)
ROADS = RoutePreferences(style=RouteStyle.ROADS)


def _index(terrains, links, roads=()):
    return build_map_index(make_map(terrains, links, roads))


def _plains(*names: str) -> dict[str, Terrain]:
    return {name: Terrain.PLAIN for name in names}


def _diamond():
    """s -> h -> g costs 200; s -> a1 -> a2 -> g costs 300."""
    names = ["reg_s", "reg_h", "reg_a1", "reg_a2", "reg_g"]
    links = [
        ("reg_s", "reg_h"),
        ("reg_h", "reg_g"),
        ("reg_s", "reg_a1"),
        ("reg_a1", "reg_a2"),
        ("reg_a2", "reg_g"),
    ]
    return _index(_plains(*names), links)


def _plan(index, preferences, hazards=frozenset(), goal="reg_g", tuning=TUNING):
    return plan_route(index, tuning, "reg_s", goal, preferences, hazards)


def test_fastest_matches_the_plain_cheapest_route() -> None:
    index = _diamond()
    assert _plan(index, FASTEST) == find_route(index, TUNING, "reg_s", "reg_g")
    assert _plan(index, FASTEST) == ["reg_h", "reg_g"]


def test_fastest_ignores_hazards() -> None:
    assert _plan(_diamond(), FASTEST, frozenset({"reg_h"})) == ["reg_h", "reg_g"]


def test_safest_goes_round_a_hazard_when_the_detour_is_cheaper_than_the_penalty() -> (
    None
):
    route = _plan(_diamond(), SAFEST, frozenset({"reg_h"}))
    assert route == ["reg_a1", "reg_a2", "reg_g"]


def test_safest_without_hazards_is_the_fastest_route() -> None:
    assert _plan(_diamond(), SAFEST) == ["reg_h", "reg_g"]


def test_safest_still_finds_a_route_when_every_way_is_hazardous() -> None:
    hazards = frozenset({"reg_h", "reg_a1"})
    route = _plan(_diamond(), SAFEST, hazards)
    assert route == ["reg_h", "reg_g"]


def test_safest_picks_the_way_with_fewer_hazards_when_all_are_dangerous() -> None:
    hazards = frozenset({"reg_h", "reg_a1", "reg_a2"})
    assert _plan(_diamond(), SAFEST, hazards) == ["reg_h", "reg_g"]


def test_a_zero_hazard_penalty_makes_safest_behave_like_fastest() -> None:
    tuning = MovementTuning(safest_hazard_penalty=0)
    route = _plan(_diamond(), SAFEST, frozenset({"reg_h"}), tuning=tuning)
    assert route == ["reg_h", "reg_g"]


def test_a_small_penalty_does_not_justify_a_long_detour() -> None:
    tuning = MovementTuning(safest_hazard_penalty=50)
    route = _plan(_diamond(), SAFEST, frozenset({"reg_h"}), tuning=tuning)
    assert route == ["reg_h", "reg_g"]


def test_a_hazard_on_the_goal_does_not_change_the_route() -> None:
    assert _plan(_diamond(), SAFEST, frozenset({"reg_g"})) == ["reg_h", "reg_g"]


def _road_choice():
    names = ["reg_s", "reg_r1", "reg_r2", "reg_g"]
    links = [
        ("reg_s", "reg_g"),
        ("reg_s", "reg_r1"),
        ("reg_r1", "reg_r2"),
        ("reg_r2", "reg_g"),
    ]
    roads = [("reg_s", "reg_r1"), ("reg_r1", "reg_r2"), ("reg_r2", "reg_g")]
    return _index(_plains(*names), links, roads)


def test_roads_prefers_a_road_detour_when_the_off_road_penalty_is_big_enough() -> None:
    tuning = MovementTuning(roads_off_road_penalty=80)
    route = _plan(_road_choice(), ROADS, tuning=tuning)
    assert route == ["reg_r1", "reg_r2", "reg_g"]


def test_fastest_still_takes_the_short_off_road_path() -> None:
    assert _plan(_road_choice(), FASTEST) == ["reg_g"]


def test_roads_with_no_roads_available_matches_fastest() -> None:
    index = _diamond()
    assert _plan(index, ROADS) == _plan(index, FASTEST)


def test_a_zero_off_road_penalty_makes_roads_behave_like_fastest() -> None:
    tuning = MovementTuning(roads_off_road_penalty=0)
    index = _road_choice()
    assert _plan(index, ROADS, tuning=tuning) == _plan(index, FASTEST)


def test_avoided_regions_are_never_entered() -> None:
    preferences = RoutePreferences(avoid=frozenset({"reg_h"}))
    assert _plan(_diamond(), preferences) == ["reg_a1", "reg_a2", "reg_g"]


def test_avoiding_every_way_gives_no_route() -> None:
    preferences = RoutePreferences(avoid=frozenset({"reg_h", "reg_a1"}))
    assert _plan(_diamond(), preferences) is None


def test_avoiding_the_goal_gives_no_route() -> None:
    preferences = RoutePreferences(avoid=frozenset({"reg_g"}))
    assert _plan(_diamond(), preferences) is None


def test_a_via_region_forces_the_route_through_it() -> None:
    preferences = RoutePreferences(via=("reg_a2",))
    assert _plan(_diamond(), preferences) == ["reg_a1", "reg_a2", "reg_g"]


def _line_with_shortcuts():
    names = ["reg_s", "reg_v1", "reg_v2", "reg_g"]
    links = [
        ("reg_s", "reg_v1"),
        ("reg_v1", "reg_v2"),
        ("reg_v2", "reg_g"),
        ("reg_s", "reg_v2"),
    ]
    return _index(_plains(*names), links)


def test_vias_are_visited_in_the_order_given() -> None:
    preferences = RoutePreferences(via=("reg_v1", "reg_v2"))
    assert _plan(_line_with_shortcuts(), preferences) == [
        "reg_v1",
        "reg_v2",
        "reg_g",
    ]


def test_reversed_vias_cannot_be_honoured_without_revisiting() -> None:
    preferences = RoutePreferences(via=("reg_v2", "reg_v1"))
    assert _plan(_line_with_shortcuts(), preferences) is None


def test_a_via_that_is_the_start_or_the_goal_is_ignored() -> None:
    preferences = RoutePreferences(via=("reg_s", "reg_g"))
    assert _plan(_diamond(), preferences) == ["reg_h", "reg_g"]


def test_a_via_that_is_avoided_gives_no_route() -> None:
    preferences = RoutePreferences(via=("reg_a1",), avoid=frozenset({"reg_a1"}))
    assert _plan(_diamond(), preferences) is None


def test_an_unreachable_via_gives_no_route() -> None:
    index = _index(_plains("reg_s", "reg_g", "reg_x"), [("reg_s", "reg_g")])
    assert _plan(index, RoutePreferences(via=("reg_x",))) is None


def test_an_unknown_via_gives_no_route() -> None:
    assert _plan(_diamond(), RoutePreferences(via=("reg_zzz",))) is None


def test_a_via_route_never_repeats_a_region() -> None:
    names = ["reg_s", "reg_m", "reg_v", "reg_g"]
    links = [("reg_s", "reg_m"), ("reg_m", "reg_v"), ("reg_m", "reg_g")]
    route = _plan(_index(_plains(*names), links), RoutePreferences(via=("reg_v",)))
    assert route is None


def test_style_and_via_work_together() -> None:
    preferences = RoutePreferences(style=RouteStyle.SAFEST, via=("reg_a2",))
    route = _plan(_diamond(), preferences, frozenset({"reg_h"}))
    assert route == ["reg_a1", "reg_a2", "reg_g"]


def test_equal_cost_ties_still_break_towards_the_lower_region_id() -> None:
    names = ["reg_s", "reg_m", "reg_n", "reg_g"]
    links = [
        ("reg_s", "reg_m"),
        ("reg_s", "reg_n"),
        ("reg_m", "reg_g"),
        ("reg_n", "reg_g"),
    ]
    index = _index(_plains(*names), links)
    for preferences in (FASTEST, SAFEST, ROADS):
        assert _plan(index, preferences) == ["reg_m", "reg_g"]


def test_the_goal_equal_to_the_start_is_an_empty_route() -> None:
    assert _plan(_diamond(), SAFEST, goal="reg_s") == []


@pytest.mark.parametrize("style", list(RouteStyle))
def test_every_planned_route_is_a_walkable_simple_path(style: RouteStyle) -> None:
    index = _diamond()
    route = _plan(index, RoutePreferences(style=style), frozenset({"reg_h"}))
    stops = ["reg_s", *route]
    assert len(set(stops)) == len(stops)
    for left, right in itertools.pairwise(stops):
        assert right in index.neighbors[left]
        assert route_base_cost(index, TUNING, left, right) > 0
    assert route_total_cost(index, TUNING, "reg_s", route) > 0
