from app.engine.overtures.cards import build_overture
from app.engine.peace.pricing import price_card
from app.engine.pressure.wars import find_war, side_score
from strategy_contracts.overtures import OvertureKind
from strategy_contracts.terms import PayGoldTerm, PeaceTerm

from tests.engine.overtures.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    war_world,
)


def test_peace_offer_is_a_short_peace_proposed_by_the_npc() -> None:
    world = war_world()

    overture = build_overture(world, SCENARIO, WRATHFUL_RIVAL, OvertureKind.PEACE_OFFER)

    assert overture.card is not None
    assert overture.card.proposer_id == WRATHFUL_RIVAL
    assert overture.card.counterpart_id == PLAYER
    peace = overture.card.terms[0]
    assert isinstance(peace, PeaceTerm)
    assert peace.tier == "short"


def test_demand_never_exceeds_npc_war_score() -> None:
    world = war_world(attacker_score=60)

    overture = build_overture(world, SCENARIO, WRATHFUL_RIVAL, OvertureKind.DEMAND)

    assert overture.card is not None
    war = find_war(world, WRATHFUL_RIVAL, PLAYER)
    assert war is not None
    price = price_card(SCENARIO, overture.card, WRATHFUL_RIVAL)
    assert price.demand <= side_score(war, WRATHFUL_RIVAL)
    gold = [term for term in overture.card.terms if isinstance(term, PayGoldTerm)]
    assert gold and gold[0].payer_id == PLAYER


def test_demand_never_asks_more_gold_than_the_player_holds() -> None:
    world = war_world(attacker_score=90)
    world.factions[PLAYER].treasury = 100

    overture = build_overture(world, SCENARIO, WRATHFUL_RIVAL, OvertureKind.DEMAND)

    assert overture.card is not None
    gold = [term for term in overture.card.terms if isinstance(term, PayGoldTerm)]
    assert gold[0].amount <= 100


def test_call_for_talks_carries_no_card() -> None:
    world = war_world()

    overture = build_overture(
        world, SCENARIO, WRATHFUL_RIVAL, OvertureKind.CALL_FOR_TALKS
    )

    assert overture.card is None


def test_pretext_hides_will_and_strain_numbers() -> None:
    world = war_world(attacker_score=60)
    for kind in (
        OvertureKind.PEACE_OFFER,
        OvertureKind.DEMAND,
        OvertureKind.CALL_FOR_TALKS,
    ):
        overture = build_overture(world, SCENARIO, WRATHFUL_RIVAL, kind)
        assert not any(character.isdigit() for character in overture.pretext)
