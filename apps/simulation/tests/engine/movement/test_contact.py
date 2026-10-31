import pytest
from app.engine.movement import events
from app.engine.movement.contact import ContactKind, classify_entry, relation_status
from strategy_contracts.enums import RelationStatus, Terrain, TroopType

from tests.engine.movement.builders import (
    FACTION_A,
    FACTION_B,
    FACTION_C,
    kinds,
    make_army,
    make_map,
    make_scenario,
    make_world_for,
    move_order,
    run_movement,
)

WAR = RelationStatus.WAR
PEACE = RelationStatus.PEACE
ALLIANCE = RelationStatus.ALLIANCE
PAIR_AB = (FACTION_A, FACTION_B)
PAIR_AC = (FACTION_A, FACTION_C)
PAIR_BC = (FACTION_B, FACTION_C)

SCENARIO = make_scenario(
    make_map(
        {
            "reg_a": Terrain.PLAIN,
            "reg_b": Terrain.PLAIN,
            "reg_c": Terrain.PLAIN,
        },
        [("reg_a", "reg_b"), ("reg_b", "reg_c")],
    )
)


def _march(
    region_b_owner: str | None,
    statuses: dict[tuple[str, str], RelationStatus],
    occupants: list[tuple[str, str]] = (),
    destination: str = "reg_b",
):
    armies = [make_army("army_a", FACTION_A, "reg_a")] + [
        make_army(army_id, owner, "reg_b") for army_id, owner in occupants
    ]
    world = make_world_for(
        {"reg_a": FACTION_A, "reg_b": region_b_owner, "reg_c": None},
        armies,
        statuses,
    )
    return run_movement(world, SCENARIO, [move_order("o1", "army_a", destination)])


@pytest.mark.parametrize(
    ("status", "occupants", "owner", "expected_kind"),
    [
        (WAR, [("army_b", FACTION_B)], FACTION_B, events.CONTACT_BATTLE),
        (WAR, [("army_b", FACTION_B)], None, events.CONTACT_BATTLE),
        (PEACE, [("army_b", FACTION_B)], FACTION_B, events.BORDER_CONFRONTATION),
        (None, [("army_b", FACTION_B)], FACTION_B, events.BORDER_CONFRONTATION),
        (PEACE, [], FACTION_B, events.BORDER_CONFRONTATION),
        (None, [], FACTION_B, events.BORDER_CONFRONTATION),
        (WAR, [], FACTION_B, events.ENEMY_REGION_ENTERED),
        (ALLIANCE, [("army_b", FACTION_B)], FACTION_B, events.ARMY_ARRIVED),
        (ALLIANCE, [], FACTION_B, events.ARMY_ARRIVED),
        (PEACE, [], None, events.ARMY_ARRIVED),
        (PEACE, [], FACTION_A, events.ARMY_ARRIVED),
        (WAR, [], FACTION_A, events.ARMY_ARRIVED),
    ],
)
def test_contact_matrix(
    status: RelationStatus | None,
    occupants: list[tuple[str, str]],
    owner: str | None,
    expected_kind: str,
) -> None:
    statuses = {PAIR_AB: status} if status else {}
    result = _march(owner, statuses, occupants)
    assert expected_kind in kinds(result.events)


def test_war_contact_enters_the_region_and_opens_one_battle() -> None:
    result = _march(FACTION_B, {PAIR_AB: WAR}, [("army_b", FACTION_B)])
    world = result.world
    assert world.armies["army_a"].location_id == "reg_b"
    assert world.armies["army_a"].march is None
    assert len(world.pending_battles) == 1
    battle = world.pending_battles[0]
    assert (battle.region_id, battle.status) == ("reg_b", "awaiting_commands")
    assert battle.attacker_army_ids == ["army_a"]
    assert battle.defender_army_ids == ["army_b"]


def test_confrontation_keeps_the_army_at_the_border() -> None:
    result = _march(FACTION_B, {PAIR_AB: PEACE}, [("army_b", FACTION_B)])
    army = result.world.armies["army_a"]
    assert army.location_id == "reg_a"
    assert army.march is None
    assert army.order is None
    assert result.world.pending_battles == []


def test_a_confrontation_names_the_region_and_the_other_army() -> None:
    result = _march(FACTION_B, {PAIR_AB: PEACE}, [("army_b", FACTION_B)])
    # The army itself is not at the border region, so the event names it explicitly.
    entry = next(e for e in result.events if e.kind == events.BORDER_CONFRONTATION)
    assert entry.cause.subject_ids[:2] == ["army_a", "reg_b"]


def test_enemy_region_stops_the_march_even_with_a_route_left() -> None:
    result = _march(FACTION_B, {PAIR_AB: WAR}, destination="reg_c")
    army = result.world.armies["army_a"]
    assert army.location_id == "reg_b"
    assert army.march is None
    assert result.world.pending_battles == []


def test_battle_stops_the_march_before_the_next_region() -> None:
    result = _march(
        FACTION_B, {PAIR_AB: WAR}, [("army_b", FACTION_B)], destination="reg_c"
    )
    assert result.world.armies["army_a"].location_id == "reg_b"
    assert result.world.armies["army_a"].march is None


def test_allied_army_in_the_way_is_passed_through() -> None:
    result = _march(
        FACTION_B, {PAIR_AB: ALLIANCE}, [("army_b", FACTION_B)], destination="reg_c"
    )
    assert result.world.armies["army_a"].location_id == "reg_b"
    assert result.world.armies["army_a"].march is not None
    assert result.world.pending_battles == []


def test_only_the_hostile_army_defends_when_an_ally_stands_beside_it() -> None:
    statuses = {PAIR_AB: WAR, PAIR_AC: ALLIANCE}
    result = _march(None, statuses, [("army_b", FACTION_B), ("army_c", FACTION_C)])
    assert result.world.pending_battles[0].defender_army_ids == ["army_b"]


def test_several_hostile_armies_make_one_battle_with_all_defenders() -> None:
    result = _march(
        FACTION_B,
        {PAIR_AB: WAR},
        [("army_b1", FACTION_B), ("army_b2", FACTION_B)],
    )
    assert len(result.world.pending_battles) == 1
    assert result.world.pending_battles[0].defender_army_ids == ["army_b1", "army_b2"]


def test_a_neutral_army_beside_an_enemy_army_still_means_battle() -> None:
    statuses = {PAIR_AB: WAR, PAIR_AC: PEACE}
    result = _march(None, statuses, [("army_b", FACTION_B), ("army_c", FACTION_C)])
    assert result.world.pending_battles[0].defender_army_ids == ["army_b"]


def test_two_attackers_arriving_together_share_one_battle() -> None:
    world = make_world_for(
        {"reg_a": FACTION_A, "reg_b": FACTION_B, "reg_c": FACTION_A},
        [
            make_army("army_a1", FACTION_A, "reg_a"),
            make_army("army_a2", FACTION_A, "reg_c"),
            make_army("army_b", FACTION_B, "reg_b"),
        ],
        {PAIR_AB: WAR},
    )
    orders = [
        move_order("o1", "army_a1", "reg_b"),
        move_order("o2", "army_a2", "reg_b"),
    ]
    battles = run_movement(world, SCENARIO, orders).world.pending_battles
    assert len(battles) == 1
    assert battles[0].attacker_army_ids == ["army_a1", "army_a2"]
    assert battles[0].defender_army_ids == ["army_b"]


def test_enemies_converging_on_an_empty_region_fight_there() -> None:
    world = make_world_for(
        {"reg_a": FACTION_A, "reg_b": None, "reg_c": FACTION_B},
        [
            make_army("army_a", FACTION_A, "reg_a"),
            make_army("army_b", FACTION_B, "reg_c"),
        ],
        {PAIR_AB: WAR},
    )
    orders = [
        move_order("o1", "army_a", "reg_b"),
        move_order("o2", "army_b", "reg_b", FACTION_B),
    ]
    battle = run_movement(world, SCENARIO, orders).world.pending_battles[0]
    assert battle.region_id == "reg_b"
    assert battle.attacker_army_ids == ["army_b"]
    assert battle.defender_army_ids == ["army_a"]


def test_armies_swapping_places_at_war_fight_instead_of_passing() -> None:
    world = make_world_for(
        {"reg_a": FACTION_A, "reg_b": FACTION_B, "reg_c": None},
        [
            make_army("army_a", FACTION_A, "reg_a"),
            make_army("army_b", FACTION_B, "reg_b"),
        ],
        {PAIR_AB: WAR},
    )
    orders = [
        move_order("o1", "army_a", "reg_b"),
        move_order("o2", "army_b", "reg_a", FACTION_B),
    ]
    result = run_movement(world, SCENARIO, orders)
    assert len(result.world.pending_battles) == 1
    assert result.world.armies["army_b"].location_id == "reg_b"


def test_an_army_already_in_a_battle_does_not_march_on() -> None:
    world = make_world_for(
        {"reg_a": FACTION_A, "reg_b": FACTION_B, "reg_c": None},
        [
            make_army("army_a", FACTION_A, "reg_a"),
            make_army("army_b", FACTION_B, "reg_b"),
        ],
        {PAIR_AB: WAR},
    )
    first = run_movement(world, SCENARIO, [move_order("o1", "army_a", "reg_c")])
    second = run_movement(first.world, SCENARIO, [move_order("o2", "army_a", "reg_c")])
    assert second.world.armies["army_a"].location_id == "reg_b"
    assert "movement_order_rejected" in kinds(second.events)


def test_battle_ids_count_up_per_new_battle() -> None:
    world = make_world_for(
        {"reg_a": FACTION_A, "reg_b": FACTION_B, "reg_c": FACTION_C},
        [
            make_army("army_a1", FACTION_A, "reg_a"),
            make_army("army_a2", FACTION_A, "reg_a"),
            make_army("army_b", FACTION_B, "reg_b"),
            make_army("army_c", FACTION_C, "reg_c"),
        ],
        {PAIR_AB: WAR},
    )
    result = run_movement(world, SCENARIO, [move_order("o1", "army_a1", "reg_b")])
    assert [battle.id for battle in result.world.pending_battles] == ["battle_1"]


def test_relation_lookup_is_symmetric_and_none_when_absent() -> None:
    world = make_world_for({"reg_a": None}, [], {PAIR_AB: WAR})
    assert relation_status(world, FACTION_A, FACTION_B) is WAR
    assert relation_status(world, FACTION_B, FACTION_A) is WAR
    assert relation_status(world, FACTION_A, FACTION_C) is None


def test_classify_entry_reports_the_hostile_defenders() -> None:
    world = make_world_for(
        {"reg_a": FACTION_A, "reg_b": FACTION_B},
        [
            make_army("army_a", FACTION_A, "reg_a"),
            make_army("army_b", FACTION_B, "reg_b", {TroopType.CAVALRY: 5}),
        ],
        {PAIR_AB: WAR},
    )
    contact = classify_entry(world, world.armies["army_a"], "reg_b")
    assert contact.kind is ContactKind.BATTLE
    assert contact.defender_ids == ("army_b",)


def test_own_armies_in_a_region_never_cause_contact() -> None:
    world = make_world_for(
        {"reg_a": FACTION_A, "reg_b": FACTION_A},
        [
            make_army("army_a", FACTION_A, "reg_a"),
            make_army("army_a2", FACTION_A, "reg_b"),
        ],
    )
    contact = classify_entry(world, world.armies["army_a"], "reg_b")
    assert contact.kind is ContactKind.NONE
