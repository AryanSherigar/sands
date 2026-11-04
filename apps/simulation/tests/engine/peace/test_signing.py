from uuid import uuid4

import pytest
from app.engine import negotiation
from app.engine.diplomacy.validation import is_at_war
from app.engine.peace.signing import is_white_peace_eligible, sign_peace
from app.engine.pressure.wars import find_war
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.models.world_pressure import MediationOffer
from strategy_contracts.enums import RelationStatus, TroopType
from strategy_contracts.peace import PeaceTier
from strategy_contracts.terms import CedeRegionTerm, PayGoldTerm, ReleasePrisonersTerm

from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    break_will,
    make_peace_card,
    make_world,
    region_owned_by,
    set_score,
    set_war_relation,
)

SCENE_ID = uuid4()
TUNING = SCENARIO.tuning.peace


def _cession(world, from_id: str, to_id: str) -> CedeRegionTerm:
    return CedeRegionTerm(
        from_faction_id=from_id,
        to_faction_id=to_id,
        region_id=region_owned_by(world, from_id),
    )


def test_sign_ends_war_and_creates_truce() -> None:
    world = make_world()
    war = set_score(add_war(world), attacker=0, defender=40)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [], tier="medium")

    events = sign_peace(world, SCENARIO, card, SCENE_ID)

    assert world.wars == []
    truce = world.truces[0]
    assert (truce.tier, truce.origin_war_id) == (PeaceTier.MEDIUM, war.id)
    assert truce.expires_turn == world.clock.turn + TUNING.tier_turns[PeaceTier.MEDIUM]
    assert len(truce.signatory_leader_ids) == 2
    assert [event.kind for event in events] == ["peace_signed"]


def test_sign_transfers_cession_and_gold() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    cede = _cession(world, WRATHFUL_RIVAL, PLAYER)
    gold = PayGoldTerm(payer_id=WRATHFUL_RIVAL, payee_id=PLAYER, amount=10)
    before = world.factions[PLAYER].treasury
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [cede, gold])

    sign_peace(world, SCENARIO, card, SCENE_ID)

    assert world.regions[cede.region_id].owner_id == PLAYER
    assert world.factions[PLAYER].treasury == before + 10


def test_card_over_score_is_rejected() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=5)
    cede = _cession(world, WRATHFUL_RIVAL, PLAYER)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [cede])

    with pytest.raises(CampaignProgressError) as error:
        sign_peace(world, SCENARIO, card, SCENE_ID)

    assert error.value.code == "exceeds_score"
    assert len(world.wars) == 1


def test_card_over_score_signs_when_counterpart_will_is_broken() -> None:
    world = make_world()
    war = set_score(add_war(world), attacker=0, defender=5)
    break_will(world, WRATHFUL_RIVAL, war.id)
    cede = _cession(world, WRATHFUL_RIVAL, PLAYER)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [cede])

    sign_peace(world, SCENARIO, card, SCENE_ID)

    assert world.wars == []


def test_cession_of_unowned_region_is_rejected() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    foreign = CedeRegionTerm(
        from_faction_id=WRATHFUL_RIVAL,
        to_faction_id=PLAYER,
        region_id=region_owned_by(world, CAUTIOUS_RIVAL),
    )
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [foreign])

    with pytest.raises(CampaignProgressError) as error:
        sign_peace(world, SCENARIO, card, SCENE_ID)

    assert error.value.code == "invalid_term"


def test_double_sign_fails_without_changing_state() -> None:
    world = make_world()
    add_war(world)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [])
    sign_peace(world, SCENARIO, card, SCENE_ID)
    snapshot = world.model_dump_json()

    with pytest.raises(CampaignProgressError) as error:
        sign_peace(world, SCENARIO, card, SCENE_ID)

    assert error.value.code == "no_war"
    assert world.model_dump_json() == snapshot


def test_white_peace_requires_low_scores_and_strain() -> None:
    world = make_world()
    war = set_score(add_war(world), attacker=10, defender=10)

    assert not is_white_peace_eligible(world, SCENARIO, war)
    set_score(war, attacker=60, defender=10)
    assert not is_white_peace_eligible(world, SCENARIO, war)


def test_long_tier_without_guarantors_marks_fragile() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [], tier="generation")

    sign_peace(world, SCENARIO, card, SCENE_ID)

    assert world.truces[0].is_fragile


def test_long_tier_with_guarantor_is_not_fragile() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    card = make_peace_card(
        PLAYER, WRATHFUL_RIVAL, [], tier="generation", guarantor_ids=[CAUTIOUS_RIVAL]
    )

    sign_peace(world, SCENARIO, card, SCENE_ID)

    assert not world.truces[0].is_fragile
    assert world.truces[0].guarantor_ids == [CAUTIOUS_RIVAL]


def test_perpetual_truce_has_no_expiry_turn() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    card = make_peace_card(
        PLAYER, WRATHFUL_RIVAL, [], tier="perpetual", guarantor_ids=[CAUTIOUS_RIVAL]
    )

    sign_peace(world, SCENARIO, card, SCENE_ID)

    assert world.truces[0].expires_turn == 0


def test_find_war_matches_either_order() -> None:
    world = make_world()
    war = add_war(world)

    assert find_war(world, PLAYER, WRATHFUL_RIVAL) is war
    assert find_war(world, WRATHFUL_RIVAL, PLAYER) is war
    assert find_war(world, PLAYER, CAUTIOUS_RIVAL) is None


def test_mediation_bonus_lowers_accept_at() -> None:
    world = make_world()
    war = add_war(world)
    plain = negotiation.acceptance_range(world, SCENARIO, PLAYER, WRATHFUL_RIVAL)
    world.pressure.mediation_offers.append(
        MediationOffer(
            id="mediation_1",
            mediator_id=CAUTIOUS_RIVAL,
            war_id=war.id,
            expires_turn=world.clock.turn + 3,
        )
    )

    mediated = negotiation.acceptance_range(world, SCENARIO, PLAYER, WRATHFUL_RIVAL)

    assert plain.accept_at - mediated.accept_at == TUNING.mediation_acceptance_bonus


def test_white_peace_is_eligible_when_both_sides_are_low_and_exhausted() -> None:
    world = make_world()
    war = set_score(add_war(world), attacker=10, defender=10)
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.peace.white_peace_min_strain = 0

    assert is_white_peace_eligible(world, scenario, war)


def test_white_peace_card_with_extra_terms_is_rejected() -> None:
    world = make_world()
    set_score(add_war(world), attacker=10, defender=10)
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.peace.white_peace_min_strain = 0
    gold = PayGoldTerm(payer_id=WRATHFUL_RIVAL, payee_id=PLAYER, amount=10)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [gold], is_white_peace=True)

    with pytest.raises(CampaignProgressError) as error:
        sign_peace(world, scenario, card, SCENE_ID)

    assert error.value.code == "not_white_peace"


def test_guarantor_that_is_a_signatory_is_rejected() -> None:
    world = make_world()
    add_war(world)
    card = make_peace_card(
        PLAYER, WRATHFUL_RIVAL, [], tier="generation", guarantor_ids=[PLAYER]
    )

    with pytest.raises(CampaignProgressError) as error:
        sign_peace(world, SCENARIO, card, SCENE_ID)

    assert error.value.code == "invalid_term"


def test_closing_a_negotiation_with_a_peace_card_signs_peace() -> None:
    world = make_world()
    add_war(world)
    opened = negotiation.open_negotiation(world, WRATHFUL_RIVAL, "peace-1")
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [])

    closed, events = negotiation.close_negotiation(
        opened, SCENARIO, opened.progress.pending_scene_id, card
    )

    assert closed.wars == []
    assert [event.kind for event in events] == ["peace_signed"]


def test_a_peace_scene_can_open_with_a_faction_at_war() -> None:
    world = make_world()
    add_war(world)

    opened = negotiation.open_negotiation(world, WRATHFUL_RIVAL, "peace-2")

    assert opened.progress.negotiation_counterpart_id == WRATHFUL_RIVAL


def test_signing_returns_the_relation_to_peace() -> None:
    world = make_world()
    add_war(world)
    set_war_relation(world, PLAYER, WRATHFUL_RIVAL)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [])

    sign_peace(world, SCENARIO, card, SCENE_ID)

    assert world.relations[0].status is RelationStatus.PEACE
    assert not is_at_war(world, PLAYER, WRATHFUL_RIVAL)


def _held_prisoner(world, holder: str, origin: str, prisoner_id: str = "prisoner_1"):
    prisoner = PrisonerState(
        id=prisoner_id,
        held_by_id=holder,
        origin_faction_id=origin,
        kind=PrisonerKind.TROOPS,
        troop_count=8,
        origin_battle_id="battle_1",
        troops_by_type={TroopType.INFANTRY: 8},
    )
    world.prisoners.append(prisoner)
    return prisoner


def test_release_prisoners_term_frees_them_and_pays_the_ransom() -> None:
    world = make_world()
    add_war(world)
    _held_prisoner(world, PLAYER, WRATHFUL_RIVAL)
    term = ReleasePrisonersTerm(
        holder_id=PLAYER,
        recipient_id=WRATHFUL_RIVAL,
        prisoner_ids=["prisoner_1"],
        ransom_gold=30,
    )
    before = world.factions[PLAYER].treasury
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [term])

    sign_peace(world, SCENARIO, card, SCENE_ID)

    assert world.prisoners == []
    assert world.factions[PLAYER].treasury == before + 30


def test_release_term_for_a_prisoner_not_held_is_rejected() -> None:
    world = make_world()
    add_war(world)
    _held_prisoner(world, WRATHFUL_RIVAL, PLAYER)
    term = ReleasePrisonersTerm(
        holder_id=PLAYER, recipient_id=WRATHFUL_RIVAL, prisoner_ids=["prisoner_1"]
    )
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [term])

    with pytest.raises(CampaignProgressError) as error:
        sign_peace(world, SCENARIO, card, SCENE_ID)

    assert error.value.code == "invalid_term"


def test_gold_the_payer_does_not_have_is_rejected() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    world.factions[WRATHFUL_RIVAL].treasury = 5
    gold = PayGoldTerm(payer_id=WRATHFUL_RIVAL, payee_id=PLAYER, amount=10)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [gold])

    with pytest.raises(CampaignProgressError) as error:
        sign_peace(world, SCENARIO, card, SCENE_ID)

    assert error.value.code == "cannot_pay"


def test_card_proposed_by_a_faction_outside_the_war_is_rejected() -> None:
    world = make_world()
    add_war(world)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, []).model_copy(
        update={"proposer_id": CAUTIOUS_RIVAL}
    )

    with pytest.raises(CampaignProgressError) as error:
        sign_peace(world, SCENARIO, card, SCENE_ID)

    assert error.value.code == "invalid_term"
    assert len(world.wars) == 1


def test_long_stalemate_allows_white_peace_without_strain() -> None:
    world = make_world()
    war = set_score(add_war(world), attacker=10, defender=10)
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.peace = scenario.tuning.peace.model_copy(
        update={"stalemate_white_peace_turns": 5}
    )
    world.pressure.stalemate_turns[war.id] = 4
    assert not is_white_peace_eligible(world, scenario, war)

    world.pressure.stalemate_turns[war.id] = 5

    assert is_white_peace_eligible(world, scenario, war)
