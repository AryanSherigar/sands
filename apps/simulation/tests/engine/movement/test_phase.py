import itertools

import pytest
from app.engine.movement import events
from app.models.orders import QueuedOrder, SetTaxRateOrder
from app.models.world_character import CommanderState, CommanderStatus
from app.models.world_events import PendingBattle
from strategy_contracts.enums import OrderKind, TaxRate, Terrain, TroopType

from tests.engine.movement.builders import (
    FACTION_A,
    FACTION_B,
    WINTER_START_MONTH,
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

CHAIN = ["reg_a", "reg_b", "reg_c", "reg_d", "reg_e"]
LINKS = list(itertools.pairwise(CHAIN))


def _chain(terrain: Terrain = Terrain.PLAIN, roads=(), **tuning):
    terrains = {name: terrain for name in CHAIN}
    return make_scenario(make_map(terrains, LINKS, roads), **tuning)


def _world(start_month: int = 6, **army_fields):
    army = make_army("army_a", FACTION_A, "reg_a", **army_fields)
    owners = {name: FACTION_A for name in CHAIN}
    return make_world_for(owners, [army], start_month=start_month)


def _location(world, army_id: str = "army_a") -> str:
    return world.armies[army_id].location_id


def test_a_one_leg_march_on_plains_finishes_in_one_turn() -> None:
    result = run_movement(_world(), _chain(), [move_order("o1", "army_a", "reg_b")])
    army = result.world.armies["army_a"]
    assert (army.location_id, army.march, army.order) == ("reg_b", None, None)
    assert kinds(result.events) == [events.MARCH_STARTED, events.ARMY_ARRIVED]


def test_a_longer_march_takes_one_leg_per_turn_on_plains() -> None:
    world, _ = play_turns(_world(), _chain(), 2, [move_order("o1", "army_a", "reg_c")])
    assert _location(world) == "reg_c"


def test_the_army_is_between_regions_when_the_turn_ends_mid_march() -> None:
    world, played = play_turns(
        _world(), _chain(), 1, [move_order("o1", "army_a", "reg_c")]
    )
    army = world.armies["army_a"]
    assert army.location_id == "reg_b"
    assert (army.march.from_id, army.march.to_id) == ("reg_b", "reg_c")
    assert army.order.kind is OrderKind.MOVE_ARMY
    assert army.order.target_id == "reg_c"
    assert events.ARMY_EN_ROUTE in kinds(played)


def test_a_mountain_pass_takes_exactly_three_turns() -> None:
    scenario = _chain(Terrain.MOUNTAIN)
    order = [move_order("o1", "army_a", "reg_b")]
    first, _ = play_turns(_world(), scenario, 1, order)
    assert first.armies["army_a"].march.leg_progress == 100
    second, _ = play_turns(first, scenario, 1)
    assert second.armies["army_a"].march.leg_progress == 200
    third, _ = play_turns(second, scenario, 1)
    assert _location(third) == "reg_b"
    assert third.armies["army_a"].march is None


def test_a_road_lets_the_army_cover_two_legs_in_a_turn() -> None:
    roads = [("reg_a", "reg_b"), ("reg_b", "reg_c")]
    result = run_movement(
        _world(), _chain(roads=roads), [move_order("o1", "army_a", "reg_c")]
    )
    assert _location(result.world) == "reg_c"
    assert kinds(result.events).count(events.ARMY_MOVED) == 1


def test_leftover_budget_after_a_finished_leg_starts_the_next_one() -> None:
    roads = [("reg_a", "reg_b")]
    scenario = _chain(roads=roads)
    result = run_movement(_world(), scenario, [move_order("o1", "army_a", "reg_c")])
    army = result.world.armies["army_a"]
    assert army.location_id == "reg_b"
    assert army.march.leg_progress == 50


def test_winter_slows_the_same_march() -> None:
    scenario = _chain()
    order = [move_order("o1", "army_a", "reg_b")]
    summer = run_movement(_world(6), scenario, order).world
    winter = run_movement(_world(WINTER_START_MONTH), scenario, order).world
    assert _location(summer) == "reg_b"
    assert _location(winter) == "reg_a"
    assert winter.armies["army_a"].march.leg_progress == 100


def test_winter_march_finishes_next_turn_when_the_season_eases() -> None:
    world, _ = play_turns(
        _world(WINTER_START_MONTH), _chain(), 2, [move_order("o1", "army_a", "reg_b")]
    )
    assert _location(world) == "reg_b"


def test_a_big_army_is_slower_than_a_small_one() -> None:
    scenario = _chain()
    order = [move_order("o1", "army_a", "reg_b")]
    big = _world(troops={TroopType.INFANTRY: 3000})
    assert _location(run_movement(big, scenario, order).world) == "reg_a"
    assert _location(run_movement(_world(), scenario, order).world) == "reg_b"


def test_a_cavalry_army_covers_more_ground() -> None:
    scenario = _chain(Terrain.HILLS, budget_per_turn=120)
    order = [move_order("o1", "army_a", "reg_b")]
    cavalry = _world(troops={TroopType.CAVALRY: 100})
    slow = _world()
    assert _location(run_movement(cavalry, scenario, order).world) == "reg_b"
    assert _location(run_movement(slow, scenario, order).world) == "reg_a"


def test_a_shaken_army_marches_slower() -> None:
    scenario = _chain()
    order = [move_order("o1", "army_a", "reg_b")]
    shaken = _world(morale=0)
    assert _location(run_movement(shaken, scenario, order).world) == "reg_a"


def test_event_cause_lists_every_reason_for_the_slowdown() -> None:
    result = run_movement(
        _world(WINTER_START_MONTH, morale=20),
        _chain(Terrain.HILLS),
        [move_order("o1", "army_a", "reg_b")],
    )
    entry = next(e for e in result.events if e.kind == events.ARMY_EN_ROUTE)
    assert entry.cause.inputs == {
        "base_cost": 150,
        "total_cost": 150 * 165 // 100,
        "adjust_winter": 50,
        "adjust_morale": 15,
        "leg_progress": 100,
    }


def test_arrival_event_records_the_location_change() -> None:
    result = run_movement(_world(), _chain(), [move_order("o1", "army_a", "reg_b")])
    arrived = next(e for e in result.events if e.kind == events.ARMY_ARRIVED)
    change = arrived.changes[0]
    assert (change.path, change.before, change.after) == (
        "armies.army_a.location_id",
        "reg_a",
        "reg_b",
    )


def test_halting_mid_leg_leaves_the_army_on_the_road() -> None:
    scenario = _chain(Terrain.MOUNTAIN)
    moving, _ = play_turns(_world(), scenario, 1, [move_order("o1", "army_a", "reg_b")])
    halted = run_movement(moving, scenario, [halt_order("o2", "army_a")]).world
    army = halted.armies["army_a"]
    assert army.location_id == "reg_a"
    assert army.march.is_halted is True
    assert army.march.leg_progress == 100
    assert army.march.route == []
    assert army.order is None


def test_a_halted_army_makes_no_progress() -> None:
    scenario = _chain(Terrain.MOUNTAIN)
    moving, _ = play_turns(_world(), scenario, 1, [move_order("o1", "army_a", "reg_b")])
    halted = run_movement(moving, scenario, [halt_order("o2", "army_a")]).world
    later, _ = play_turns(halted, scenario, 3)
    assert later.armies["army_a"].march.leg_progress == 100
    assert _location(later) == "reg_a"


def test_halting_before_any_progress_clears_the_march() -> None:
    world = _world()
    first = run_movement(
        world, _chain(Terrain.MOUNTAIN), [move_order("o1", "army_a", "reg_c")]
    )
    army = first.world.armies["army_a"]
    assert army.march.leg_progress == 100
    fresh = _world()
    fresh.armies["army_a"].march = None
    halt = run_movement(fresh, _chain(), [halt_order("o1", "army_a")])
    assert halt.events == []


def test_a_halted_army_can_resume_and_keeps_its_progress() -> None:
    scenario = _chain(Terrain.MOUNTAIN)
    moving, _ = play_turns(_world(), scenario, 1, [move_order("o1", "army_a", "reg_b")])
    halted = run_movement(moving, scenario, [halt_order("o2", "army_a")]).world
    resumed = run_movement(
        halted, scenario, [move_order("o3", "army_a", "reg_b")]
    ).world
    assert resumed.armies["army_a"].march.is_halted is False
    assert resumed.armies["army_a"].march.leg_progress == 200


def test_a_halted_army_can_be_sent_further_along_the_same_road() -> None:
    scenario = _chain(Terrain.MOUNTAIN)
    moving, _ = play_turns(_world(), scenario, 1, [move_order("o1", "army_a", "reg_b")])
    halted = run_movement(moving, scenario, [halt_order("o2", "army_a")]).world
    resumed = run_movement(
        halted, scenario, [move_order("o3", "army_a", "reg_d")]
    ).world
    march = resumed.armies["army_a"].march
    assert (march.to_id, march.route) == ("reg_b", ["reg_c", "reg_d"])


def test_mid_leg_the_army_walks_back_when_the_way_round_is_far_longer() -> None:
    links = [*LINKS, ("reg_a", "reg_e")]
    terrains = {name: Terrain.MOUNTAIN for name in CHAIN}
    started = make_scenario(make_map(terrains, links))
    slow = make_scenario(make_map(terrains, links), budget_per_turn=1)
    moving, _ = play_turns(_world(), started, 1, [move_order("o1", "army_a", "reg_b")])
    result = run_movement(moving, slow, [move_order("o2", "army_a", "reg_e")])
    march = result.world.armies["army_a"].march
    assert (march.is_returning, march.route) == (True, ["reg_e"])


def test_mid_leg_the_army_continues_forward_when_the_origin_is_a_dead_end() -> None:
    terrains = {name: Terrain.PLAIN for name in CHAIN}
    started = make_scenario(make_map(terrains, LINKS), budget_per_turn=60)
    slow = make_scenario(make_map(terrains, LINKS), budget_per_turn=1)
    moving, _ = play_turns(_world(), started, 1, [move_order("o1", "army_a", "reg_b")])
    result = run_movement(moving, slow, [move_order("o2", "army_a", "reg_e")])
    march = result.world.armies["army_a"].march
    assert (march.is_returning, march.to_id) == (False, "reg_b")
    assert march.route == ["reg_c", "reg_d", "reg_e"]


def _rejection(world, scenario, orders) -> str:
    result = run_movement(world, scenario, orders)
    assert result.world == world
    entry = result.events[0]
    assert entry.kind == events.ORDER_REJECTED
    return entry.cause.summary_key.removeprefix(f"{events.ORDER_REJECTED}_")


def test_moving_another_factions_army_is_rejected() -> None:
    order = move_order("o1", "army_a", "reg_b", FACTION_B)
    assert _rejection(_world(), _chain(), [order]) == "not_your_army"


def test_moving_an_unknown_army_is_rejected() -> None:
    order = move_order("o1", "army_zzz", "reg_b")
    assert _rejection(_world(), _chain(), [order]) == "unknown_army"


def test_an_order_for_an_unknown_faction_is_rejected() -> None:
    order = move_order("o1", "army_a", "reg_b", "house_nobody")
    assert _rejection(_world(), _chain(), [order]) == "not_your_army"


def test_an_empty_army_cannot_march() -> None:
    world = _world(troops={TroopType.INFANTRY: 0})
    assert (
        _rejection(world, _chain(), [move_order("o1", "army_a", "reg_b")])
        == "empty_army"
    )


def test_a_destroyed_factions_army_cannot_march() -> None:
    world = _world()
    world.factions[FACTION_A].is_destroyed = True
    reason = _rejection(world, _chain(), [move_order("o1", "army_a", "reg_b")])
    assert reason == "faction_destroyed"


@pytest.mark.parametrize("status", [CommanderStatus.CAPTURED, CommanderStatus.DEAD])
def test_an_army_whose_commander_is_gone_cannot_march(status: CommanderStatus) -> None:
    world = _world()
    world.armies["army_a"].commander_id = "cmd_renaud"
    world.commanders["cmd_renaud"] = CommanderState(
        id="cmd_renaud",
        name="Renaud",
        faction_id=FACTION_A,
        army_id="army_a",
        status=status,
    )
    reason = _rejection(world, _chain(), [move_order("o1", "army_a", "reg_b")])
    assert reason == "commander_unavailable"


def test_an_army_in_a_pending_battle_cannot_march() -> None:
    world = _world()
    world.pending_battles.append(
        PendingBattle(
            id="battle_1",
            region_id="reg_a",
            attacker_army_ids=["army_a"],
            defender_army_ids=["army_x"],
            is_big=False,
            status="awaiting_commands",
        )
    )
    assert (
        _rejection(world, _chain(), [move_order("o1", "army_a", "reg_b")])
        == "in_battle"
    )


def test_a_resolved_battle_no_longer_holds_the_army() -> None:
    world = _world()
    world.pending_battles.append(
        PendingBattle(
            id="battle_1",
            region_id="reg_a",
            attacker_army_ids=["army_a"],
            defender_army_ids=["army_x"],
            is_big=False,
            status="resolved",
        )
    )
    result = run_movement(world, _chain(), [move_order("o1", "army_a", "reg_b")])
    assert _location(result.world) == "reg_b"


def test_an_unknown_destination_is_rejected() -> None:
    order = move_order("o1", "army_a", "reg_zzz")
    assert _rejection(_world(), _chain(), [order]) == "unknown_region"


def test_ordering_an_army_to_where_it_stands_is_rejected() -> None:
    order = move_order("o1", "army_a", "reg_a")
    assert _rejection(_world(), _chain(), [order]) == "already_there"


def test_a_destination_with_no_route_is_rejected() -> None:
    terrains = {name: Terrain.PLAIN for name in ("reg_a", "reg_b", "reg_c")}
    scenario = make_scenario(make_map(terrains, [("reg_a", "reg_b")]))
    world = make_world_for(
        {name: FACTION_A for name in terrains},
        [make_army("army_a", FACTION_A, "reg_a")],
    )
    assert (
        _rejection(world, scenario, [move_order("o1", "army_a", "reg_c")]) == "no_route"
    )


def test_two_orders_for_one_army_keep_the_lowest_id_and_reject_the_rest() -> None:
    orders = [move_order("o2", "army_a", "reg_c"), move_order("o1", "army_a", "reg_b")]
    result = run_movement(_world(), _chain(), orders)
    assert _location(result.world) == "reg_b"
    rejected = [e for e in result.events if e.kind == events.ORDER_REJECTED]
    assert [e.cause.summary_key for e in rejected] == [
        f"{events.ORDER_REJECTED}_duplicate_order"
    ]


def test_a_move_then_a_halt_for_the_same_army_keeps_only_the_move() -> None:
    orders = [move_order("o1", "army_a", "reg_b"), halt_order("o2", "army_a")]
    result = run_movement(_world(), _chain(), orders)
    assert _location(result.world) == "reg_b"


def test_halting_someone_elses_army_is_rejected() -> None:
    world = _world()
    assert (
        _rejection(world, _chain(), [halt_order("o1", "army_a", FACTION_B)])
        == "not_your_army"
    )


def test_other_order_kinds_are_left_alone() -> None:
    order = QueuedOrder(
        id="o1",
        order=SetTaxRateOrder(faction_id=FACTION_A, tax_rate=TaxRate.HIGH),
        cost=1,
        queued_turn=0,
    )
    world = _world()
    result = run_movement(world, _chain(), [order])
    assert result.world == world
    assert result.events == []


def test_a_march_survives_a_turn_where_nothing_changes_the_season() -> None:
    scenario = _chain(Terrain.MOUNTAIN)
    world, _ = play_turns(_world(), scenario, 2, [move_order("o1", "army_a", "reg_b")])
    assert world.armies["army_a"].march.leg_progress == 200


def test_events_use_the_movement_phase() -> None:
    result = run_movement(_world(), _chain(), [move_order("o1", "army_a", "reg_b")])
    assert {entry.phase.value for entry in result.events} == {"movement"}


def test_an_idle_world_produces_no_events_and_no_changes() -> None:
    world = _world()
    result = run_movement(world, _chain())
    assert result.events == []
    assert result.world == world
