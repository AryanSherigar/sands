import pytest
from app.engine.movement.route_preview import preview_routes
from app.models.api_route_preview import RoutePreview, RouteWarning, WarningKind
from app.models.orders import MoveArmyOrder, QueuedOrder
from strategy_contracts.enums import RelationStatus, RouteStyle, Terrain

from tests.engine.movement.builders import (
    FACTION_A,
    FACTION_B,
    WINTER_START_MONTH,
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
WAR = {(FACTION_A, FACTION_B): RelationStatus.WAR}


def _scenario(terrain: Terrain = Terrain.PLAIN, **tuning):
    return make_scenario(make_map({n: terrain for n in NAMES}, LINKS), **tuning)


def _world(h_owner=FACTION_B, statuses=PEACE, start_month=6, extra=()):
    owners = dict.fromkeys(NAMES, FACTION_A)
    owners["reg_h"] = h_owner
    armies = [make_army("army_a", FACTION_A, "reg_s"), *extra]
    return make_world_for(owners, armies, statuses, start_month=start_month)


def _preview(world, scenario, **kwargs) -> list[RoutePreview]:
    return preview_routes(
        world, scenario, "army_a", kwargs.pop("to", "reg_g"), **kwargs
    )


def _by_route(previews):
    return {tuple(preview.route): preview for preview in previews}


def test_styles_that_agree_are_merged_into_one_option() -> None:
    previews = _preview(_world(h_owner=FACTION_A), _scenario())
    assert len(previews) == 1
    assert previews[0].styles == [
        RouteStyle.FASTEST,
        RouteStyle.SAFEST,
        RouteStyle.ROADS,
    ]


def test_a_hazard_splits_fastest_and_safest_into_two_options() -> None:
    previews = _preview(_world(), _scenario())
    by_route = _by_route(previews)
    assert by_route[("reg_h", "reg_g")].styles == [RouteStyle.FASTEST, RouteStyle.ROADS]
    assert by_route[("reg_a1", "reg_a2", "reg_g")].styles == [RouteStyle.SAFEST]
    assert [preview.styles[0] for preview in previews] == [
        RouteStyle.FASTEST,
        RouteStyle.SAFEST,
    ]


def test_base_cost_is_the_season_free_point_total() -> None:
    by_route = _by_route(_preview(_world(), _scenario(Terrain.PLAIN)))
    assert by_route[("reg_h", "reg_g")].base_cost == 200
    assert by_route[("reg_a1", "reg_a2", "reg_g")].base_cost == 300


def test_estimated_turns_follow_the_real_cost_rules() -> None:
    by_route = _by_route(_preview(_world(), _scenario()))
    assert by_route[("reg_h", "reg_g")].estimated_turns == 2
    assert by_route[("reg_a1", "reg_a2", "reg_g")].estimated_turns == 3


def test_winter_makes_the_same_route_take_longer() -> None:
    summer = _preview(_world(h_owner=FACTION_A), _scenario())[0]
    winter = _preview(
        _world(h_owner=FACTION_A, start_month=WINTER_START_MONTH), _scenario()
    )[0]
    assert summer.estimated_turns == 2
    assert winter.estimated_turns == 3


def test_a_foreign_owner_at_peace_is_a_closed_border_warning() -> None:
    fastest = _by_route(_preview(_world(), _scenario()))[("reg_h", "reg_g")]
    assert fastest.warnings == [
        RouteWarning(kind=WarningKind.CLOSED_BORDER, region_id="reg_h")
    ]


def test_the_safe_option_carries_no_warnings() -> None:
    safe = _by_route(_preview(_world(), _scenario()))[("reg_a1", "reg_a2", "reg_g")]
    assert safe.warnings == []


def test_an_enemy_owned_region_warns_of_enemy_territory() -> None:
    fastest = _by_route(_preview(_world(statuses=WAR), _scenario()))[("reg_h", "reg_g")]
    assert fastest.warnings[0].kind is WarningKind.ENEMY_TERRITORY


def test_a_visible_enemy_army_warns_of_battle() -> None:
    enemy = make_army("army_b", FACTION_B, "reg_h")
    previews = _preview(_world(statuses=WAR, extra=[enemy]), _scenario())
    fastest = _by_route(previews)[("reg_h", "reg_g")]
    assert fastest.warnings[0].kind is WarningKind.HOSTILE_ARMY


def test_no_warning_for_land_the_player_cannot_see() -> None:
    owners = dict.fromkeys(NAMES, None)
    owners["reg_s"] = FACTION_A
    owners["reg_g"] = FACTION_B
    world = make_world_for(owners, [make_army("army_a", FACTION_A, "reg_s")], PEACE)
    preview = _preview(world, _scenario())[0]
    assert preview.warnings == []


def test_via_and_avoid_shape_every_option() -> None:
    previews = _preview(_world(), _scenario(), via=("reg_a2",))
    assert {tuple(p.route) for p in previews} == {("reg_a1", "reg_a2", "reg_g")}
    avoided = _preview(
        _world(h_owner=FACTION_A), _scenario(), avoid=frozenset({"reg_h"})
    )
    assert {tuple(p.route) for p in avoided} == {("reg_a1", "reg_a2", "reg_g")}


@pytest.mark.parametrize("destination", ["reg_zzz", "reg_s"])
def test_an_impossible_destination_gives_no_options(destination: str) -> None:
    assert _preview(_world(), _scenario(), to=destination) == []


def test_avoiding_the_destination_gives_no_options() -> None:
    assert _preview(_world(), _scenario(), avoid=frozenset({"reg_g"})) == []


def test_an_unknown_army_gives_no_options() -> None:
    assert preview_routes(_world(), _scenario(), "army_zzz", "reg_g") == []


def test_previewing_never_changes_the_world() -> None:
    world = _world()
    snapshot = world.model_dump()
    _preview(world, _scenario())
    assert world.model_dump() == snapshot


def test_previews_are_deterministic() -> None:
    assert _preview(_world(), _scenario()) == _preview(_world(), _scenario())


@pytest.mark.parametrize("style", list(RouteStyle))
def test_each_preview_matches_what_an_order_with_that_style_does(
    style: RouteStyle,
) -> None:
    world, scenario = _world(), _scenario(budget_per_turn=1)
    preview = next(p for p in _preview(world, scenario) if style in p.styles)
    order = MoveArmyOrder(
        faction_id=FACTION_A, army_id="army_a", to_region_id="reg_g", route_style=style
    )
    queued = QueuedOrder(id="o1", order=order, cost=1, queued_turn=0)
    march = run_movement(world, scenario, [queued]).world.armies["army_a"].march
    assert [march.to_id, *march.route] == preview.route


def test_an_army_on_the_road_gets_a_turn_back_option_with_its_walk_back_cost() -> None:
    scenario = _scenario(Terrain.MOUNTAIN)
    order = MoveArmyOrder(faction_id=FACTION_A, army_id="army_a", to_region_id="reg_a1")
    moving, _ = play_turns(
        _world(h_owner=FACTION_A),
        scenario,
        1,
        [QueuedOrder(id="o1", order=order, cost=1, queued_turn=0)],
    )
    previews = preview_routes(moving, scenario, "army_a", "reg_s")
    assert len(previews) == 1
    assert previews[0].is_turning_back is True
    assert previews[0].base_cost == 100
    assert previews[0].estimated_turns == 1


def test_the_estimate_is_capped() -> None:
    scenario = _scenario(Terrain.MOUNTAIN, budget_per_turn=1)
    preview = _preview(_world(h_owner=FACTION_A), scenario)[0]
    assert preview.estimated_turns == 60


def _turns_the_real_march_takes(world, scenario, destination: str) -> int:
    order = MoveArmyOrder(
        faction_id=FACTION_A, army_id="army_a", to_region_id=destination
    )
    queued = QueuedOrder(id="o1", order=order, cost=1, queued_turn=0)
    for turns in range(1, 61):
        final, _ = play_turns(world, scenario, turns, [queued])
        if final.armies["army_a"].location_id == destination:
            return turns
    return 60


@pytest.mark.parametrize("start_month", range(1, 13))
@pytest.mark.parametrize("terrain", [Terrain.PLAIN, Terrain.MARSH, Terrain.MOUNTAIN])
def test_the_estimate_equals_the_turns_the_real_march_takes(
    start_month: int, terrain: Terrain
) -> None:
    world = _world(h_owner=FACTION_A, start_month=start_month)
    scenario = _scenario(terrain)
    preview = _preview(world, scenario)[0]
    actual = _turns_the_real_march_takes(world, scenario, "reg_g")
    assert preview.estimated_turns == actual
