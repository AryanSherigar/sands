from app.engine.movement.map_index import build_map_index
from app.models.api_world_view import SiegeView
from app.models.world_character import CommanderState
from app.models.world_region import RegionIntel
from app.services.world_projection import own_armies, project_region
from strategy_contracts.enums import PayLevel, Terrain
from tests.engine.movement.builders import (
    FACTION_A,
    make_army,
    make_map,
    make_scenario,
    make_world_for,
)
from tests.engine.sieges.builders import (
    BESIEGER,
    SCENARIO,
    TARGET_REGION,
    add_siege,
    make_siege_world,
    occupy,
)


def test_fogged_region_uses_stale_observation_not_current_state() -> None:
    scenario = make_scenario(
        make_map({"home": Terrain.PLAIN, "hidden": Terrain.PLAIN}, [])
    )
    world = make_world_for({"home": FACTION_A, "hidden": "house_c"}, turn=8)
    world.factions[FACTION_A].intel["hidden"] = RegionIntel(
        last_seen_turn=4,
        owner_id="house_b",
        garrison_low=20,
        garrison_high=40,
    )

    view = project_region(
        world,
        "hidden",
        FACTION_A,
        build_map_index(scenario.map),
        frozenset({"home"}),
    )

    assert view.owner_id == "house_b"
    assert view.last_seen_turn == 4
    assert view.garrison_estimate is not None
    assert view.garrison_estimate.high == 40


def test_own_armies_includes_pay_level() -> None:
    army = make_army("army_1", FACTION_A, "home")
    army.pay_level = PayLevel.REDUCED
    world = make_world_for({"home": FACTION_A}, armies=[army])

    views = own_armies(world, FACTION_A)

    assert len(views) == 1
    assert views[0].pay_level == PayLevel.REDUCED


def test_own_armies_names_the_commander_leading_the_army() -> None:
    army = make_army("army_1", FACTION_A, "home")
    army.commander_id = "cmd_1"
    world = make_world_for({"home": FACTION_A}, armies=[army])
    world.commanders["cmd_1"] = CommanderState(
        id="cmd_1", name="Ser Aldric", faction_id=FACTION_A, army_id="army_1"
    )

    views = own_armies(world, FACTION_A)

    assert views[0].commander_name == "Ser Aldric"


def test_own_armies_leaves_an_unled_army_unnamed() -> None:
    army = make_army("army_1", FACTION_A, "home")
    world = make_world_for({"home": FACTION_A}, armies=[army])

    assert own_armies(world, FACTION_A)[0].commander_name is None


def _siege_projection(visible: frozenset[str]):
    world = make_siege_world()
    add_siege(world, progress=40)
    occupy(world, hold_turns=1)
    return project_region(
        world,
        TARGET_REGION,
        BESIEGER,
        build_map_index(SCENARIO.map),
        visible,
    )


def test_visible_region_shows_its_occupation() -> None:
    view = _siege_projection(frozenset({TARGET_REGION}))

    assert view.occupation is not None
    assert (view.occupation.occupier_id, view.occupation.hold_turns) == (BESIEGER, 1)


def test_visible_region_shows_its_siege_progress() -> None:
    view = _siege_projection(frozenset({TARGET_REGION}))

    assert view.siege == SiegeView(besieger_id=BESIEGER, progress=40)


def test_fogged_region_hides_siege_and_occupation() -> None:
    view = _siege_projection(frozenset())

    assert view.occupation is None
    assert view.siege is None
