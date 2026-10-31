import pytest
from app.engine.diplomacy.grounds import grant_ground
from app.exceptions.command_exceptions import CommandError
from app.models.orders import (
    CallNegotiationOrder,
    DeclareWarOrder,
    DiplomaticPlayOrder,
    FabricateClaimOrder,
)
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.enums import RelationStatus
from strategy_contracts.terms import CedeRegionTerm, NonAggressionTerm, PayGoldTerm

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    queue_npc_order,
    set_traits,
)

ACTOR = WRATHFUL_RIVAL
TARGET = CAUTIOUS_RIVAL


def _declare(target: str = TARGET, ground_id: str | None = None) -> DeclareWarOrder:
    return DeclareWarOrder(
        faction_id=ACTOR, target_faction_id=target, ground_id=ground_id
    )


def _demand(target: str = TARGET, region: str = "elmstead") -> DiplomaticPlayOrder:
    return DiplomaticPlayOrder(
        faction_id=ACTOR,
        target_faction_id=target,
        demands=[
            CedeRegionTerm(
                from_faction_id=target, to_faction_id=ACTOR, region_id=region
            )
        ],
    )


def _code(world, order) -> str:
    before = world.factions[order.faction_id].orders_remaining
    with pytest.raises(CommandError) as raised:
        queue_npc_order(world, SCENARIO, order)
    assert world.factions[order.faction_id].orders_remaining == before
    return raised.value.code


def test_legacy_world_rejects_diplomacy_orders() -> None:
    world = make_world()
    world.diplomacy_ruleset = 0

    assert _code(world, _declare()) == "diplomacy_disabled"


def test_unknown_self_and_destroyed_targets_are_rejected() -> None:
    world = make_world()
    assert _code(world, _declare("nobody")) == "unknown_target"
    assert _code(world, _declare(ACTOR)) == "self_target"
    world.factions[TARGET].is_destroyed = True
    assert _code(world, _declare()) == "target_destroyed"


def test_leaderless_target_is_rejected() -> None:
    world = make_world()
    world.factions[TARGET].leader_id = None

    assert _code(world, _declare()) == "no_leader"


def test_war_against_a_faction_already_at_war_is_rejected() -> None:
    world = make_world()
    for relation in world.relations:
        if {relation.faction_a, relation.faction_b} == {ACTOR, TARGET}:
            relation.status = RelationStatus.WAR

    assert _code(world, _declare()) == "already_at_war"


def test_unknown_and_unusable_grounds_are_rejected() -> None:
    world = make_world()
    assert _code(world, _declare(ground_id="ground_9")) == "unknown_ground"
    ground = grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.CLAIM,
        holder_faction_id=ACTOR,
        target_faction_id=TARGET,
        region_id="elmstead",
    )
    ground.strength = 5

    assert _code(world, _declare(ground_id=ground.id)) == "ground_not_usable"


def test_demand_and_call_aimed_at_the_player_are_rejected() -> None:
    world = make_world()

    assert _code(world, _demand(PLAYER, "brennmoor")) == "target_is_player"
    call = CallNegotiationOrder(faction_id=ACTOR, target_faction_id=PLAYER)
    assert _code(world, call) == "target_is_player"


def test_unsupported_and_malformed_demand_terms_are_rejected() -> None:
    world = make_world()
    pact = NonAggressionTerm(faction_a=ACTOR, faction_b=TARGET, duration_turns=3)
    unsupported = DiplomaticPlayOrder(
        faction_id=ACTOR, target_faction_id=TARGET, demands=[pact]
    )
    assert _code(world, unsupported) == "term_not_supported"
    assert _code(world, _demand(region="aldgate")) == "bad_demand_term"
    wrong_payer = DiplomaticPlayOrder(
        faction_id=ACTOR,
        target_faction_id=TARGET,
        demands=[PayGoldTerm(payer_id=ACTOR, payee_id=TARGET, amount=10)],
    )
    assert _code(world, wrong_payer) == "bad_demand_term"


def test_forging_needs_a_cunning_ruler_and_a_real_target_region() -> None:
    world = make_world()
    forge = FabricateClaimOrder(
        faction_id=ACTOR, target_faction_id=TARGET, region_id="elmstead"
    )
    assert (
        _code(
            world,
            FabricateClaimOrder(
                faction_id=ACTOR, target_faction_id=TARGET, region_id="mars"
            ),
        )
        == "region_unknown"
    )
    set_traits(world, ACTOR, ["honorable"])

    assert _code(world, forge) == "not_cunning"


def test_declare_war_costs_two_orders_and_demand_costs_one() -> None:
    world = make_world()
    queued = queue_npc_order(world, SCENARIO, _declare(PLAYER))
    assert queued.factions[ACTOR].orders_remaining == 4

    queued = queue_npc_order(world, SCENARIO, _demand())
    assert queued.factions[ACTOR].orders_remaining == 5


def test_second_demand_to_same_target_same_turn_is_a_duplicate_slot() -> None:
    world = queue_npc_order(make_world(), SCENARIO, _demand())

    assert _code(world, _demand()) == "duplicate_slot"
