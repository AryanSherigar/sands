from app.engine.diplomacy.war_declaration import declare_war
from app.engine.pressure.shocks import detect_state_shocks, record_shock, shock_total
from app.models.orders import DeclareWarOrder
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.models.world_region import OccupationState
from strategy_contracts.pressure import ShockKind

from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

AMOUNTS = SCENARIO.tuning.pressure.shock_amounts


def test_shock_fires_once_per_war_and_faction() -> None:
    world = make_world()
    war = add_war(world)

    first = record_shock(world, SCENARIO, ShockKind.CAPITAL_FALLS, PLAYER, war.id)
    second = record_shock(world, SCENARIO, ShockKind.CAPITAL_FALLS, PLAYER, war.id)

    assert (first, second) == (True, False)
    assert len(world.pressure.shocks) == 1


def test_shock_total_sums_recorded_amounts_for_the_faction() -> None:
    world = make_world()
    war = add_war(world)
    record_shock(world, SCENARIO, ShockKind.CAPITAL_FALLS, PLAYER, war.id)
    record_shock(world, SCENARIO, ShockKind.NEW_ENEMY, PLAYER, war.id)
    record_shock(world, SCENARIO, ShockKind.NEW_ENEMY, WRATHFUL_RIVAL, war.id)

    expected = AMOUNTS[ShockKind.CAPITAL_FALLS] + AMOUNTS[ShockKind.NEW_ENEMY]
    assert shock_total(world, SCENARIO, PLAYER) == expected


def test_declare_war_on_busy_defender_records_new_enemy_shock() -> None:
    world = make_world()
    add_war(world, attacker_id=CAUTIOUS_RIVAL, defender_id=PLAYER)

    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )

    kinds = {(s.faction_id, s.kind) for s in world.pressure.shocks}
    assert kinds == {(PLAYER, ShockKind.NEW_ENEMY)}


def test_declare_war_on_idle_defender_records_no_shock() -> None:
    world = make_world()

    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )

    assert world.pressure.shocks == []


def test_capital_occupation_records_capital_falls_once() -> None:
    world = make_world()
    add_war(world)
    capital = world.regions[world.factions[PLAYER].capital_region_id]
    capital.occupation = OccupationState(occupier_id=WRATHFUL_RIVAL, siege_progress=100)

    detect_state_shocks(world, SCENARIO)
    detect_state_shocks(world, SCENARIO)

    kinds = [s.kind for s in world.pressure.shocks if s.faction_id == PLAYER]
    assert kinds == [ShockKind.CAPITAL_FALLS]


def test_ruler_capture_records_shock() -> None:
    world = make_world()
    add_war(world)
    leader_id = world.factions[PLAYER].leader_id
    world.prisoners.append(
        PrisonerState(
            id="p1",
            held_by_id=WRATHFUL_RIVAL,
            origin_faction_id=PLAYER,
            kind=PrisonerKind.CHARACTER,
            character_id=leader_id,
        )
    )

    detect_state_shocks(world, SCENARIO)

    assert ShockKind.RULER_CAPTURED in {s.kind for s in world.pressure.shocks}


def test_dead_ruler_records_shock() -> None:
    world = make_world()
    add_war(world)
    world.leaders[world.factions[PLAYER].leader_id].is_alive = False

    detect_state_shocks(world, SCENARIO)

    assert ShockKind.RULER_CAPTURED in {s.kind for s in world.pressure.shocks}


def test_destroyed_home_army_records_shock() -> None:
    world = make_world()
    add_war(world)
    for army in world.armies.values():
        if army.owner_id == PLAYER:
            army.troops = {}

    detect_state_shocks(world, SCENARIO)

    assert ShockKind.HOME_ARMY_DESTROYED in {s.kind for s in world.pressure.shocks}


def test_no_shocks_for_factions_at_peace() -> None:
    world = make_world()
    world.leaders[world.factions[PLAYER].leader_id].is_alive = False

    detect_state_shocks(world, SCENARIO)

    assert world.pressure.shocks == []
