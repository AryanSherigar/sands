from app.engine.movement.engagement import armies_in_open_battle, open_or_join_battle
from app.models.world_army import MarchState
from app.models.world_events import PendingBattle
from app.models.world_state import CounterKind

from tests.engine.movement.builders import (
    FACTION_A,
    FACTION_B,
    make_army,
    make_world_for,
)


def _world():
    return make_world_for(
        {"reg_a": FACTION_A, "reg_b": FACTION_B},
        [
            make_army("army_a1", FACTION_A, "reg_a"),
            make_army("army_a2", FACTION_A, "reg_a"),
            make_army("army_b1", FACTION_B, "reg_b"),
            make_army("army_b2", FACTION_B, "reg_b"),
        ],
    )


def test_a_new_battle_takes_the_next_counter_id() -> None:
    world = _world()
    first = open_or_join_battle(world, "reg_b", ["army_a1"], ["army_b1"])
    second = open_or_join_battle(world, "reg_a", ["army_b2"], ["army_a2"])
    assert (first.id, second.id) == ("battle_1", "battle_2")
    assert world.counters[CounterKind.BATTLE] == 2


def test_joining_an_open_battle_merges_both_sides_sorted() -> None:
    world = _world()
    open_or_join_battle(world, "reg_b", ["army_a2"], ["army_b2"])
    battle = open_or_join_battle(world, "reg_b", ["army_a1"], ["army_b1"])
    assert battle.attacker_army_ids == ["army_a1", "army_a2"]
    assert battle.defender_army_ids == ["army_b1", "army_b2"]
    assert len(world.pending_battles) == 1


def test_an_army_already_defending_never_also_attacks() -> None:
    world = _world()
    open_or_join_battle(world, "reg_b", ["army_a1"], ["army_b1"])
    battle = open_or_join_battle(world, "reg_b", ["army_b1"], [])
    assert battle.attacker_army_ids == ["army_a1"]
    assert battle.defender_army_ids == ["army_b1"]


def test_an_army_already_attacking_is_never_added_as_a_defender() -> None:
    world = _world()
    open_or_join_battle(world, "reg_b", ["army_a1"], ["army_b1"])
    battle = open_or_join_battle(world, "reg_b", [], ["army_a1"])
    assert battle.attacker_army_ids == ["army_a1"]
    assert battle.defender_army_ids == ["army_b1"]


def test_joining_twice_does_not_duplicate_anyone() -> None:
    world = _world()
    open_or_join_battle(world, "reg_b", ["army_a1"], ["army_b1"])
    battle = open_or_join_battle(world, "reg_b", ["army_a1"], ["army_b1"])
    assert battle.attacker_army_ids == ["army_a1"]
    assert battle.defender_army_ids == ["army_b1"]


def test_a_resolved_battle_is_not_joined_a_new_one_opens() -> None:
    world = _world()
    world.pending_battles.append(
        PendingBattle(
            id="battle_9",
            region_id="reg_b",
            attacker_army_ids=["army_a1"],
            defender_army_ids=["army_b1"],
            is_big=False,
            status="resolved",
        )
    )
    open_or_join_battle(world, "reg_b", ["army_a2"], ["army_b2"])
    assert len(world.pending_battles) == 2
    assert armies_in_open_battle(world) == {"army_a2", "army_b2"}


def test_everyone_in_a_battle_stops_marching() -> None:
    world = _world()
    world.armies["army_a1"].march = MarchState(from_id="reg_a", to_id="reg_b")
    world.armies["army_b1"].march = MarchState(from_id="reg_b", to_id="reg_a")
    open_or_join_battle(world, "reg_b", ["army_a1"], ["army_b1"])
    assert world.armies["army_a1"].march is None
    assert world.armies["army_b1"].march is None
