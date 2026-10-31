import pytest
from app.engine.diplomacy.phase import DiplomacyPhase
from app.exceptions.command_exceptions import CommandError
from app.models.orders import SendEnvoyOrder
from app.models.world_diplomacy import RelationState
from strategy_contracts.enums import RelationStatus

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    queue_npc_order,
    run_phase,
)
from tests.engine.pressure.builders import add_war


def _envoy(target: str = CAUTIOUS_RIVAL, sender: str = PLAYER) -> SendEnvoyOrder:
    return SendEnvoyOrder(faction_id=sender, target_faction_id=target)


def _code(world, order) -> str:
    before = world.factions[order.faction_id].orders_remaining
    with pytest.raises(CommandError) as raised:
        queue_npc_order(world, SCENARIO, order)
    assert world.factions[order.faction_id].orders_remaining == before
    return raised.value.code


def test_send_envoy_creates_envoy_and_costs_order() -> None:
    world = make_world()
    before = world.factions[PLAYER].orders_remaining
    queued = queue_npc_order(world, SCENARIO, _envoy())

    result = run_phase(DiplomacyPhase(), queued)

    envoys = result.world.envoys
    assert [(e.from_faction_id, e.at_faction_id) for e in envoys] == [
        (PLAYER, CAUTIOUS_RIVAL)
    ]
    assert (
        result.world.factions[PLAYER].orders_remaining
        == before - (SCENARIO.tuning.order_costs["send_envoy"])
    )
    assert [e.kind for e in result.events] == ["envoy_sent"]


def test_duplicate_envoy_is_rejected() -> None:
    world = make_world()
    world = run_phase(
        DiplomacyPhase(), queue_npc_order(world, SCENARIO, _envoy())
    ).world

    world.clock.turn += 1

    assert _code(world, _envoy()) == "envoy_already_there"


def test_envoy_to_self_unknown_or_destroyed_faction_is_rejected() -> None:
    world = make_world()
    assert _code(world, _envoy(PLAYER)) == "self_target"
    assert _code(world, _envoy("nobody")) == "unknown_target"
    world.factions[CAUTIOUS_RIVAL].is_destroyed = True
    assert _code(world, _envoy(CAUTIOUS_RIVAL)) == "target_destroyed"


def test_envoy_to_a_faction_at_war_with_the_sender_is_rejected() -> None:
    world = make_world()
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)
    world.relations.append(_war_relation(PLAYER, WRATHFUL_RIVAL, world.clock.turn))

    assert _code(world, _envoy(WRATHFUL_RIVAL)) == "already_at_war"


def _war_relation(first: str, second: str, turn: int):
    low, high = sorted((first, second))
    return RelationState(
        faction_a=low, faction_b=high, status=RelationStatus.WAR, since_turn=turn
    )
