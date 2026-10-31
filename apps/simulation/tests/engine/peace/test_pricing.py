from app.engine.peace.pricing import (
    CardPrice,
    can_afford,
    is_will_broken,
    price_card,
)
from strategy_contracts.terms import CedeRegionTerm, PayGoldTerm

from tests.engine.peace.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    break_will,
    make_peace_card,
    make_world,
    region_owned_by,
    set_score,
)

TUNING = SCENARIO.tuning.peace


def test_price_sums_tier_and_cession_costs() -> None:
    world = make_world()
    region = region_owned_by(world, WRATHFUL_RIVAL)
    cede = CedeRegionTerm(
        from_faction_id=WRATHFUL_RIVAL, to_faction_id=PLAYER, region_id=region
    )
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [cede], tier="medium")

    price = price_card(SCENARIO, card, PLAYER)

    assert price == CardPrice(demand=TUNING.cede_region_score_cost + 5, concession=0)


def test_paying_gold_is_a_concession() -> None:
    gold = PayGoldTerm(payer_id=PLAYER, payee_id=WRATHFUL_RIVAL, amount=100)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [gold])

    price = price_card(SCENARIO, card, PLAYER)

    assert price == CardPrice(demand=0, concession=100 // TUNING.gold_per_score_point)


def test_card_over_score_is_not_affordable() -> None:
    world = make_world()
    war = set_score(add_war(world), attacker=0, defender=10)
    region = region_owned_by(world, WRATHFUL_RIVAL)
    cede = CedeRegionTerm(
        from_faction_id=WRATHFUL_RIVAL, to_faction_id=PLAYER, region_id=region
    )
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [cede])

    assert not can_afford(world, SCENARIO, card, PLAYER, war)


def test_card_over_score_is_affordable_when_counterpart_will_is_broken() -> None:
    world = make_world()
    war = set_score(add_war(world), attacker=0, defender=10)
    break_will(world, WRATHFUL_RIVAL, war.id)
    region = region_owned_by(world, WRATHFUL_RIVAL)
    cede = CedeRegionTerm(
        from_faction_id=WRATHFUL_RIVAL, to_faction_id=PLAYER, region_id=region
    )
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [cede])

    assert is_will_broken(world, SCENARIO, WRATHFUL_RIVAL)
    assert can_afford(world, SCENARIO, card, PLAYER, war)


def test_faction_without_shocks_is_not_broken() -> None:
    world = make_world()
    add_war(world)

    assert not is_will_broken(world, SCENARIO, WRATHFUL_RIVAL)
