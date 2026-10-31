from app.engine.economy.income import faction_income
from app.engine.opinion import opinion_of
from app.engine.vassals.consequences import apply_reply
from app.engine.vassals.registry import vassalage_of
from strategy_contracts.vassal import DemandKind, DemandReply

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    add_vassalage,
    make_demand,
    make_world,
)

TUNING = SCENARIO.tuning.vassal


def _treasuries(world) -> tuple[int, int]:
    return world.factions[PLAYER].treasury, world.factions[CAUTIOUS_RIVAL].treasury


def _setup(tribute=20, asked=60):
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].treasury = 10_000
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, tribute=tribute)
    return world, make_demand(commitment, DemandKind.TRIBUTE, asked)


def _income(world) -> int:
    return faction_income(world, SCENARIO.tuning.economy, CAUTIOUS_RIVAL).total


def test_accept_transfers_the_asked_tribute_once() -> None:
    world, demand = _setup()
    before = _treasuries(world)
    expected = _income(world) * 60 // 100

    apply_reply(world, SCENARIO, demand, DemandReply.ACCEPT)

    assert _treasuries(world) == (before[0] + expected, before[1] - expected)


def test_counter_pays_granted_plus_half_the_excess() -> None:
    world, demand = _setup()
    before = _treasuries(world)
    expected = _income(world) * (20 + (60 - 20) // 2) // 100

    apply_reply(world, SCENARIO, demand, DemandReply.COUNTER)

    assert _treasuries(world) == (before[0] + expected, before[1] - expected)


def test_refuse_costs_opinion_and_adds_grievance_and_pays_nothing() -> None:
    world, demand = _setup()
    before = _treasuries(world)
    leader = world.leaders[world.factions[CAUTIOUS_RIVAL].leader_id]
    overlord_leader = world.factions[PLAYER].leader_id
    opinion = opinion_of(leader, overlord_leader)

    apply_reply(world, SCENARIO, demand, DemandReply.REFUSE)

    assert _treasuries(world) == before
    assert opinion_of(leader, overlord_leader) == opinion - TUNING.refuse_opinion_cost
    [standing] = world.vassal.standing
    assert standing.grievance == TUNING.refuse_grievance


def test_strong_refusal_costs_more_and_raises_more_unrest() -> None:
    world, demand = _setup()
    leader = world.leaders[world.factions[CAUTIOUS_RIVAL].leader_id]
    overlord_leader = world.factions[PLAYER].leader_id
    opinion = opinion_of(leader, overlord_leader)
    unrest = sum(
        r.unrest for r in world.regions.values() if r.owner_id == CAUTIOUS_RIVAL
    )

    apply_reply(world, SCENARIO, demand, DemandReply.REFUSE_STRONGLY)

    assert opinion_of(leader, overlord_leader) == opinion - TUNING.strong_opinion_cost
    assert world.vassal.standing[0].grievance == TUNING.strong_grievance
    assert (
        sum(r.unrest for r in world.regions.values() if r.owner_id == CAUTIOUS_RIVAL)
        > unrest
    )


def test_accepted_garrison_demand_opens_temporary_access() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    demand = make_demand(commitment, DemandKind.GARRISON, 1)

    apply_reply(world, SCENARIO, demand, DemandReply.ACCEPT)

    assert world.vassal.garrison_until[commitment.id] == (
        world.clock.turn + TUNING.garrison_demand_turns
    )


def test_rebel_reply_records_the_rebellion_event() -> None:
    world, demand = _setup()

    events = apply_reply(world, SCENARIO, demand, DemandReply.REBEL)

    assert "vassal_rebelled" in [event.kind for event in events]
    assert vassalage_of(world, CAUTIOUS_RIVAL) is None
