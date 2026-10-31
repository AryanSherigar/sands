import itertools

from app.engine.movement.costs import route_total_cost
from app.engine.movement.knowledge import known_hazards
from app.engine.movement.map_index import build_map_index
from app.engine.movement.pathing import find_route
from app.engine.movement.route_options import RoutePreferences, plan_route
from app.engine.movement.route_preview import preview_routes
from app.models.orders import MoveArmyOrder, QueuedOrder
from hypothesis import given, settings
from hypothesis import strategies as st
from strategy_contracts.enums import RouteStyle

from tests.engine.movement.builders import run_movement
from tests.engine.movement.test_invariants import PROPERTY_SETTINGS, games

ROUTE_SETTINGS = settings(parent=PROPERTY_SETTINGS, max_examples=30)

ROUTE_REASONS = ("no_route", "avoid_blocks_goal", "already_there", "unknown_region")


@st.composite
def route_cases(draw):
    world, scenario, _ = draw(games())
    index = build_map_index(scenario.map)
    names = sorted(index.terrain)
    start, goal = draw(st.sampled_from(names)), draw(st.sampled_from(names))
    others = [name for name in names if name not in (start, goal)]
    via = (
        draw(st.lists(st.sampled_from(others), unique=True, max_size=2))
        if others
        else []
    )
    pool = [name for name in names if name not in via]
    avoid = draw(st.sets(st.sampled_from(pool), max_size=3))
    hazards = draw(st.sets(st.sampled_from(names), max_size=4))
    return (
        world,
        scenario,
        index,
        start,
        goal,
        tuple(via),
        frozenset(avoid),
        frozenset(hazards),
    )


def _off_road_legs(index, start, route) -> int:
    stops = [start, *route]
    return sum(
        not index.has_road(left, right) for left, right in itertools.pairwise(stops)
    )


def _hazard_count(route, hazards) -> int:
    return sum(region in hazards for region in route)


@ROUTE_SETTINGS
@given(route_cases(), st.sampled_from(list(RouteStyle)))
def test_every_planned_route_honours_the_players_choices(case, style) -> None:
    _, scenario, index, start, goal, via, avoid, hazards = case
    tuning = scenario.tuning.movement
    preferences = RoutePreferences(style=style, via=via, avoid=avoid)
    route = plan_route(index, tuning, start, goal, preferences, hazards)
    if route is None:
        return
    stops = [start, *route]
    assert len(set(stops)) == len(stops)
    assert (route[-1] if route else start) == goal
    assert not set(route) & avoid
    for left, right in itertools.pairwise(stops):
        assert right in index.neighbors[left]
    waypoints = [region for region in via if region not in (start, goal)]
    visited = [region for region in route if region in waypoints]
    assert visited == waypoints


@ROUTE_SETTINGS
@given(route_cases())
def test_fastest_without_choices_is_exactly_the_old_cheapest_route(case) -> None:
    _, scenario, index, start, goal, _, _, hazards = case
    tuning = scenario.tuning.movement
    planned = plan_route(index, tuning, start, goal, RoutePreferences(), hazards)
    assert planned == find_route(index, tuning, start, goal)


@ROUTE_SETTINGS
@given(route_cases())
def test_fastest_is_never_dearer_in_points_than_the_other_styles(case) -> None:
    _, scenario, index, start, goal, _, _, hazards = case
    tuning = scenario.tuning.movement
    fastest = plan_route(index, tuning, start, goal, RoutePreferences(), hazards)
    if fastest is None:
        return
    base = route_total_cost(index, tuning, start, fastest)
    for style in (RouteStyle.SAFEST, RouteStyle.ROADS):
        other = plan_route(
            index, tuning, start, goal, RoutePreferences(style=style), hazards
        )
        assert route_total_cost(index, tuning, start, other) >= base


@ROUTE_SETTINGS
@given(route_cases())
def test_safest_never_enters_more_hazards_and_roads_never_more_off_road_legs(
    case,
) -> None:
    _, scenario, index, start, goal, _, _, hazards = case
    tuning = scenario.tuning.movement
    fastest = plan_route(index, tuning, start, goal, RoutePreferences(), hazards)
    if fastest is None:
        return
    safest = plan_route(
        index, tuning, start, goal, RoutePreferences(style=RouteStyle.SAFEST), hazards
    )
    roads = plan_route(
        index, tuning, start, goal, RoutePreferences(style=RouteStyle.ROADS), hazards
    )
    assert _hazard_count(safest, hazards) <= _hazard_count(fastest, hazards)
    assert _off_road_legs(index, start, roads) <= _off_road_legs(index, start, fastest)


@ROUTE_SETTINGS
@given(route_cases(), st.randoms(use_true_random=False))
def test_the_plan_does_not_depend_on_the_order_links_were_listed(
    case, shuffler
) -> None:
    _, scenario, index, start, goal, via, avoid, hazards = case
    tuning = scenario.tuning.movement
    shuffled = scenario.map.model_copy(deep=True)
    shuffler.shuffle(shuffled.regions)
    for region in shuffled.regions:
        shuffler.shuffle(region.neighbor_ids)
    shuffler.shuffle(shuffled.roads)
    other = build_map_index(shuffled)
    for style in RouteStyle:
        preferences = RoutePreferences(style=style, via=via, avoid=avoid)
        first = plan_route(index, tuning, start, goal, preferences, hazards)
        second = plan_route(other, tuning, start, goal, preferences, hazards)
        assert first == second


@ROUTE_SETTINGS
@given(route_cases(), st.sampled_from(list(RouteStyle)))
def test_what_the_preview_shows_is_what_the_order_does(case, style) -> None:
    world, scenario, _, _, goal, via, avoid, _ = case
    army = world.armies["army_0"]
    options = preview_routes(world, scenario, army.id, goal, via, avoid)
    order = MoveArmyOrder(
        faction_id=army.owner_id,
        army_id=army.id,
        to_region_id=goal,
        route_style=style,
        via_region_ids=list(via),
        avoid_region_ids=sorted(avoid),
    )
    queued = QueuedOrder(id="o1", order=order, cost=1, queued_turn=0)
    slow = scenario.model_copy(
        update={
            "tuning": scenario.tuning.model_copy(
                update={
                    "movement": scenario.tuning.movement.model_copy(
                        update={"budget_per_turn": 1}
                    )
                }
            )
        }
    )
    result = run_movement(world, slow, [queued])
    march = result.world.armies[army.id].march
    previewed = [option for option in options if style in option.styles]
    rejected = [e for e in result.events if e.kind == "movement_order_rejected"]
    if march is not None and not army.march:
        assert previewed
        assert previewed[0].route == [march.to_id, *march.route]
    if rejected and rejected[0].cause.summary_key.endswith(ROUTE_REASONS):
        assert not previewed


@ROUTE_SETTINGS
@given(route_cases())
def test_planning_and_previewing_never_change_the_world(case) -> None:
    world, scenario, index, start, goal, via, avoid, hazards = case
    snapshot = world.model_dump()
    plan_route(
        index,
        scenario.tuning.movement,
        start,
        goal,
        RoutePreferences(via=via, avoid=avoid),
        hazards,
    )
    preview_routes(world, scenario, "army_0", goal, via, avoid)
    known_hazards(world, "house_a", index)
    assert world.model_dump() == snapshot
