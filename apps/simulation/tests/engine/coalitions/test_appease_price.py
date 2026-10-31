from app.engine.coalitions.appease import does_member_accept, member_price, offer_value
from strategy_contracts.coalition import ClaimCessionOffer, GoldOffer, PactOffer
from strategy_contracts.traits import TraitDefinition

from tests.engine.coalitions.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    resent,
)

TUNING = SCENARIO.tuning.coalition
HUGE_PACT_TURNS = 1000
HUGE_GOLD = 10_000


def test_cautious_member_is_cheaper_than_proud_member() -> None:
    world = make_world()
    resent(world, WRATHFUL_RIVAL, PLAYER)
    resent(world, CAUTIOUS_RIVAL, PLAYER)
    scenario = SCENARIO.model_copy(
        update={
            "custom_traits": [
                TraitDefinition(id="wary", name="wary", effects={"caution": 3}),
                TraitDefinition(id="vain", name="vain", effects={"pride": 3}),
            ]
        }
    )
    world.leaders[world.factions[CAUTIOUS_RIVAL].leader_id].trait_ids = ["wary"]
    world.leaders[world.factions[WRATHFUL_RIVAL].leader_id].trait_ids = ["vain"]

    cautious = member_price(world, scenario, CAUTIOUS_RIVAL, PLAYER)
    proud = member_price(world, scenario, WRATHFUL_RIVAL, PLAYER)

    assert cautious < proud


def test_deeper_resentment_raises_price() -> None:
    world = make_world()
    resent(world, WRATHFUL_RIVAL, PLAYER)
    once = member_price(world, SCENARIO, WRATHFUL_RIVAL, PLAYER)
    resent(world, WRATHFUL_RIVAL, PLAYER)

    twice = member_price(world, SCENARIO, WRATHFUL_RIVAL, PLAYER)

    assert twice > once


def test_pact_value_is_capped() -> None:
    world = make_world()

    value = offer_value(world, SCENARIO, PactOffer(duration_turns=HUGE_PACT_TURNS))

    assert value == TUNING.appease_pact_max_value


def test_pact_alone_cannot_buy_hostile_member() -> None:
    world = make_world()
    resent(world, WRATHFUL_RIVAL, PLAYER)
    resent(world, WRATHFUL_RIVAL, PLAYER)
    offer = PactOffer(duration_turns=HUGE_PACT_TURNS)

    assert not does_member_accept(world, SCENARIO, WRATHFUL_RIVAL, PLAYER, offer)


def test_gold_scales_with_amount() -> None:
    world = make_world()

    small = offer_value(world, SCENARIO, GoldOffer(amount=10))
    large = offer_value(world, SCENARIO, GoldOffer(amount=50))

    assert large > small


def test_enough_gold_buys_a_resentful_member() -> None:
    world = make_world()
    resent(world, WRATHFUL_RIVAL, PLAYER)

    assert does_member_accept(
        world, SCENARIO, WRATHFUL_RIVAL, PLAYER, GoldOffer(amount=HUGE_GOLD)
    )


def test_cession_value_follows_region_wealth() -> None:
    world = make_world()
    owned = sorted(k for k, r in world.regions.items() if r.owner_id == PLAYER)
    first, second = owned[0], owned[-1]
    world.regions[first].wealth = 10
    world.regions[second].wealth = 40

    low = offer_value(world, SCENARIO, ClaimCessionOffer(region_id=first))
    high = offer_value(world, SCENARIO, ClaimCessionOffer(region_id=second))

    assert high > low
