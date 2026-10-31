from app.engine.vassals.demands import resolve_demands
from app.engine.vassals.overlord_rule import npc_overlord_demands
from app.engine.vassals.registry import vassalage_of
from strategy_contracts.vassal import DemandKind

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    add_war,
    make_world,
)

TUNING = SCENARIO.tuning.vassal


def _strained_world():
    world = make_world()
    add_vassalage(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL, tribute=20)
    world.factions[WRATHFUL_RIVAL].treasury = TUNING.overlord_strain_treasury // 2
    return world


def test_strained_npc_overlord_demands_once_then_waits_the_cooldown() -> None:
    world = _strained_world()

    first = npc_overlord_demands(world, SCENARIO)
    [demand] = world.vassal.demands
    world.clock.turn = demand.deadline_turn
    resolve_demands(world, SCENARIO)
    again_now = npc_overlord_demands(world, SCENARIO)
    world.clock.turn = demand.issued_turn + TUNING.demand_cooldown_turns
    later = npc_overlord_demands(world, SCENARIO)

    assert [e.kind for e in first] == ["demand_issued"]
    assert demand.kind is DemandKind.TRIBUTE
    assert demand.amount > demand.granted
    assert again_now == []
    assert [e.kind for e in later] == ["demand_issued"]


def test_demand_is_bounded_by_the_tuning_ceiling() -> None:
    world = _strained_world()
    world.factions[WRATHFUL_RIVAL].treasury = -10_000

    npc_overlord_demands(world, SCENARIO)

    [demand] = world.vassal.demands
    assert demand.amount - demand.granted <= TUNING.overlord_demand_max_excess_percent


def test_comfortable_npc_overlord_never_demands() -> None:
    world = make_world()
    add_vassalage(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL)
    world.factions[WRATHFUL_RIVAL].treasury = TUNING.overlord_strain_treasury * 10

    assert npc_overlord_demands(world, SCENARIO) == []


def test_overlord_losing_a_war_demands_even_with_a_full_treasury() -> None:
    world = make_world()
    add_vassalage(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL)
    world.factions[WRATHFUL_RIVAL].treasury = TUNING.overlord_strain_treasury * 10
    war = add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)
    war.war_score_attacker, war.war_score_defender = 0, 30

    assert [e.kind for e in npc_overlord_demands(world, SCENARIO)] == ["demand_issued"]


def test_player_overlord_is_never_driven_by_the_rule() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    world.factions[PLAYER].treasury = 0

    assert npc_overlord_demands(world, SCENARIO) == []
    assert vassalage_of(world, CAUTIOUS_RIVAL) is not None
