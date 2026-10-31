import itertools

import pytest
from app.engine.movement.costs import route_base_cost
from app.engine.movement.map_index import build_map_index
from app.engine.movement.pathing import find_route
from strategy_contracts.enums import Terrain
from strategy_contracts.scenario import MovementTuning

TUNING = MovementTuning()


def _index(terrains, links, roads=()):
    from tests.engine.movement.builders import make_map

    return build_map_index(make_map(terrains, links, roads))


def _plains(*names: str) -> dict[str, Terrain]:
    return {name: Terrain.PLAIN for name in names}


def test_route_between_neighbours_is_the_destination_alone() -> None:
    index = _index(_plains("reg_a", "reg_b"), [("reg_a", "reg_b")])
    assert find_route(index, TUNING, "reg_a", "reg_b") == ["reg_b"]


def test_route_to_the_start_is_empty() -> None:
    index = _index(_plains("reg_a", "reg_b"), [("reg_a", "reg_b")])
    assert find_route(index, TUNING, "reg_a", "reg_a") == []


def test_route_follows_a_chain_in_order() -> None:
    names = ["reg_a", "reg_b", "reg_c", "reg_d"]
    index = _index(_plains(*names), list(itertools.pairwise(names)))
    assert find_route(index, TUNING, "reg_a", "reg_d") == ["reg_b", "reg_c", "reg_d"]


def test_route_prefers_a_longer_road_over_a_short_mountain_pass() -> None:
    terrains = {
        "reg_a": Terrain.PLAIN,
        "reg_pass": Terrain.MOUNTAIN,
        "reg_x": Terrain.PLAIN,
        "reg_y": Terrain.PLAIN,
        "reg_goal": Terrain.PLAIN,
    }
    links = [
        ("reg_a", "reg_pass"),
        ("reg_pass", "reg_goal"),
        ("reg_a", "reg_x"),
        ("reg_x", "reg_y"),
        ("reg_y", "reg_goal"),
    ]
    roads = [("reg_a", "reg_x"), ("reg_x", "reg_y"), ("reg_y", "reg_goal")]
    index = _index(terrains, links, roads)
    assert find_route(index, TUNING, "reg_a", "reg_goal") == [
        "reg_x",
        "reg_y",
        "reg_goal",
    ]


def test_route_takes_the_short_way_when_the_detour_is_dearer() -> None:
    terrains = _plains("reg_a", "reg_b", "reg_c", "reg_d", "reg_goal")
    links = [
        ("reg_a", "reg_goal"),
        ("reg_a", "reg_b"),
        ("reg_b", "reg_c"),
        ("reg_c", "reg_goal"),
    ]
    index = _index(terrains, links)
    assert find_route(index, TUNING, "reg_a", "reg_goal") == ["reg_goal"]


def test_equal_cost_ties_break_towards_the_lower_region_id() -> None:
    terrains = _plains("reg_a", "reg_m", "reg_n", "reg_goal")
    links = [
        ("reg_a", "reg_m"),
        ("reg_a", "reg_n"),
        ("reg_m", "reg_goal"),
        ("reg_n", "reg_goal"),
    ]
    index = _index(terrains, links)
    assert find_route(index, TUNING, "reg_a", "reg_goal") == ["reg_m", "reg_goal"]


@pytest.mark.parametrize("seed", range(6))
def test_route_does_not_depend_on_link_listing_order(seed: int) -> None:
    terrains = _plains("reg_a", "reg_m", "reg_n", "reg_goal")
    links = [
        ("reg_a", "reg_m"),
        ("reg_a", "reg_n"),
        ("reg_m", "reg_goal"),
        ("reg_n", "reg_goal"),
    ]
    rotated = links[seed % len(links) :] + links[: seed % len(links)]
    if seed % 2:
        rotated = [(right, left) for left, right in reversed(rotated)]
    index = _index(terrains, rotated)
    assert find_route(index, TUNING, "reg_a", "reg_goal") == ["reg_m", "reg_goal"]


def test_unreachable_destination_gives_none() -> None:
    index = _index(_plains("reg_a", "reg_b", "reg_c"), [("reg_a", "reg_b")])
    assert find_route(index, TUNING, "reg_a", "reg_c") is None


def test_unknown_destination_gives_none() -> None:
    index = _index(_plains("reg_a", "reg_b"), [("reg_a", "reg_b")])
    assert find_route(index, TUNING, "reg_a", "reg_zzz") is None


def test_route_never_revisits_a_region_and_ends_at_the_goal() -> None:
    names = ["reg_a", "reg_b", "reg_c", "reg_d", "reg_e"]
    links = [*itertools.pairwise(names), ("reg_a", "reg_c"), ("reg_b", "reg_e")]
    index = _index(_plains(*names), links)
    route = find_route(index, TUNING, "reg_a", "reg_e")
    assert route is not None
    assert len(set(route)) == len(route)
    assert "reg_a" not in route
    assert route[-1] == "reg_e"


def test_route_cost_is_the_sum_of_its_legs() -> None:
    terrains = {
        "reg_a": Terrain.PLAIN,
        "reg_b": Terrain.HILLS,
        "reg_c": Terrain.MARSH,
    }
    index = _index(
        terrains, [("reg_a", "reg_b"), ("reg_b", "reg_c")], [("reg_b", "reg_c")]
    )
    route = find_route(index, TUNING, "reg_a", "reg_c")
    stops = ["reg_a", *route]
    total = sum(
        route_base_cost(index, TUNING, left, right)
        for left, right in itertools.pairwise(stops)
    )
    assert total == 150 + 200 * 50 // 100


def test_avoided_regions_are_routed_around() -> None:
    terrains = _plains("reg_a", "reg_m", "reg_n", "reg_goal")
    links = [
        ("reg_a", "reg_m"),
        ("reg_a", "reg_n"),
        ("reg_m", "reg_goal"),
        ("reg_n", "reg_goal"),
    ]
    index = _index(terrains, links)
    route = find_route(index, TUNING, "reg_a", "reg_goal", frozenset({"reg_m"}))
    assert route == ["reg_n", "reg_goal"]


def test_a_goal_that_must_be_avoided_has_no_route() -> None:
    index = _index(_plains("reg_a", "reg_b"), [("reg_a", "reg_b")])
    assert find_route(index, TUNING, "reg_a", "reg_b", frozenset({"reg_b"})) is None


def test_avoiding_the_only_bridge_cuts_the_map() -> None:
    names = ["reg_a", "reg_b", "reg_c"]
    index = _index(_plains(*names), list(itertools.pairwise(names)))
    assert find_route(index, TUNING, "reg_a", "reg_c", frozenset({"reg_b"})) is None
