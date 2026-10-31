from app.engine.ai.catalog import legal_candidates
from app.engine.ai.generators.movement import movement_candidates
from app.models.orders import AttackOrder, MoveArmyOrder
from app.models.world_ai import AimState
from app.models.world_army import ArmyState, MarchState
from app.models.world_diplomacy import RelationState, WarState
from strategy_contracts.enums import RelationStatus, TroopType
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

TUNING = SCENARIO.tuning.ai
BIG = "army_carrow_1"
SMALL = "army_carrow_2"


def _at_war():
    world = make_world()
    low, high = sorted((CAUTIOUS_RIVAL, WRATHFUL_RIVAL))
    world.relations = [
        RelationState(
            faction_a=low, faction_b=high, status=RelationStatus.WAR, since_turn=0
        )
    ]
    world.wars.append(
        WarState(
            id="war_1",
            attacker_id=WRATHFUL_RIVAL,
            defender_id=CAUTIOUS_RIVAL,
            started_turn=0,
        )
    )
    return world


def _candidates(world):
    return movement_candidates(world, SCENARIO, CAUTIOUS_RIVAL)


def _orders(world, order_type, army_id: str | None = None):
    return [
        item
        for item in _candidates(world)
        if isinstance(item.order, order_type)
        and (army_id is None or item.order.army_id == army_id)
    ]


def test_armies_approach_the_nearest_known_enemy_region() -> None:
    moves = _orders(_at_war(), MoveArmyOrder, BIG)
    approach = [item for item in moves if item.order.to_region_id == "fenwatch"]

    assert len(approach) == 1
    assert approach[0].category == ScoreCategory.ATTACK
    assert approach[0].base_score == TUNING.approach_bonus


def test_army_next_to_an_enemy_region_attacks_it() -> None:
    world = _at_war()
    world.armies[BIG].location_id = "high_meadow"

    attacks = _orders(world, AttackOrder, BIG)

    assert [item.order.target_region_id for item in attacks] == ["fenwatch"]
    assert attacks[0].base_score == TUNING.strike_bonus


def test_outmatched_army_attacks_only_with_a_risk_penalty() -> None:
    world = _at_war()
    world.armies[BIG].location_id = "high_meadow"
    world.armies[BIG].troops = {TroopType.INFANTRY: 10}

    attacks = _orders(world, AttackOrder, BIG)

    assert attacks[0].base_score == -TUNING.risk_penalty


def test_no_attack_or_approach_without_a_war() -> None:
    candidates = _candidates(make_world())

    assert not [item for item in candidates if isinstance(item.order, AttackOrder)]
    assert not [item for item in candidates if item.category == ScoreCategory.ATTACK]


def _attack_aim(world) -> None:
    world.aims[CAUTIOUS_RIVAL] = AimState(
        category=ScoreCategory.ATTACK,
        target_faction_id=WRATHFUL_RIVAL,
        chosen_turn=0,
        leader_id=world.factions[CAUTIOUS_RIVAL].leader_id,
        capital_held=True,
    )


def test_attack_aim_without_war_masses_armies_on_the_border() -> None:
    world = make_world()
    _attack_aim(world)

    moves = _orders(world, MoveArmyOrder)
    staged = {item.order.army_id: item.order.to_region_id for item in moves}

    assert staged[SMALL] == "high_meadow"
    assert all(
        item.category == ScoreCategory.ATTACK
        for item in moves
        if item.order.to_region_id == "high_meadow"
    )


def test_army_already_on_the_border_stays_put() -> None:
    world = make_world()
    _attack_aim(world)
    world.armies[SMALL].location_id = "high_meadow"

    moves = _orders(world, MoveArmyOrder, SMALL)

    assert all(item.order.to_region_id != "high_meadow" for item in moves)


def _hostile_at_kings_ford(world) -> None:
    world.armies["raider"] = ArmyState(
        id="raider",
        owner_id=WRATHFUL_RIVAL,
        troops={TroopType.INFANTRY: 50},
        morale=60,
        location_id="kings_ford",
    )


def test_nearest_idle_army_defends_a_threatened_region() -> None:
    world = _at_war()
    _hostile_at_kings_ford(world)

    defenders = [
        item
        for item in _orders(world, MoveArmyOrder)
        if item.category == ScoreCategory.BUILD
    ]

    assert [(i.order.army_id, i.order.to_region_id) for i in defenders] == [
        (SMALL, "high_meadow")
    ]
    assert defenders[0].base_score == TUNING.defense_bonus


def test_army_expands_into_one_adjacent_neutral_region() -> None:
    world = make_world()

    expansion = [
        item
        for item in _orders(world, MoveArmyOrder, BIG)
        if item.category == ScoreCategory.EXPAND
    ]

    assert [item.order.to_region_id for item in expansion] == ["kings_ford"]


def test_marching_armies_get_no_new_orders() -> None:
    world = _at_war()
    world.armies[BIG].march = MarchState(from_id="carrow_vale", to_id="kings_ford")

    assert _orders(world, MoveArmyOrder, BIG) == []


def test_changes_inside_the_fog_do_not_change_the_candidates() -> None:
    world = _at_war()
    baseline = _candidates(world)
    world.regions["brennmoor"].owner_id = WRATHFUL_RIVAL
    world.armies["army_dunwick_1"].location_id = "brennmoor"
    world.regions["dunwick"].garrison = 999

    assert _candidates(world) == baseline


def test_war_candidates_are_legal_orders() -> None:
    world = _at_war()
    world.armies[SMALL].location_id = "high_meadow"
    candidates = _candidates(world)

    legal = legal_candidates(world, SCENARIO, CAUTIOUS_RIVAL, candidates)

    assert any(isinstance(item.order, AttackOrder) for item in legal)
    assert any(isinstance(item.order, MoveArmyOrder) for item in legal)
