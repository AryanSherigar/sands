import pytest
from app.engine.alliances.registry import set_pair_relation
from app.engine.negotiation import apply_terms_card
from app.engine.vassals.acceptance import does_counterpart_accept_vassalage
from app.engine.vassals.pricing import vassal_price
from app.engine.vassals.registry import vassalage_of
from app.engine.vassals.signing import sign_vassalage
from app.exceptions.command_exceptions import CampaignProgressError
from strategy_contracts.enums import RelationStatus
from strategy_contracts.terms import TermsCard
from strategy_contracts.vassal import VassalTier, VassalTuning, tier_term

from tests.engine.alliances.builders import add_alliance
from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    SCENE_ID,
    WRATHFUL_RIVAL,
    add_vassalage,
    make_vassal_term,
    make_world,
    set_war_relation,
)

TUNING = VassalTuning()


def _relation_status(world, first: str, second: str) -> RelationStatus | None:
    pair = tuple(sorted((first, second)))
    return next(
        (
            item.status
            for item in world.relations
            if (item.faction_a, item.faction_b) == pair
        ),
        None,
    )


def test_sign_creates_active_commitment_and_keeps_peace_relation() -> None:
    world = make_world()
    set_pair_relation(world, PLAYER, CAUTIOUS_RIVAL, RelationStatus.PEACE)

    events = sign_vassalage(
        world, SCENARIO, make_vassal_term(PLAYER, CAUTIOUS_RIVAL), SCENE_ID
    )

    assert vassalage_of(world, CAUTIOUS_RIVAL) is not None
    assert _relation_status(world, PLAYER, CAUTIOUS_RIVAL) == RelationStatus.PEACE
    assert [event.kind for event in events] == ["vassalage_signed"]


def test_forever_vassalage_has_no_end_turn() -> None:
    world = make_world()

    assert add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, duration=0).end_turn is None


def test_fixed_vassalage_ends_after_its_duration() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, duration=6)

    assert commitment.end_turn == world.clock.turn + 6


def test_self_vassalage_is_rejected() -> None:
    with pytest.raises(CampaignProgressError):
        sign_vassalage(
            make_world(), SCENARIO, make_vassal_term(PLAYER, PLAYER), SCENE_ID
        )


def test_unknown_faction_is_rejected() -> None:
    with pytest.raises(CampaignProgressError):
        sign_vassalage(
            make_world(), SCENARIO, make_vassal_term(PLAYER, "nobody"), SCENE_ID
        )


def test_destroyed_faction_is_rejected() -> None:
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].is_destroyed = True

    with pytest.raises(CampaignProgressError):
        sign_vassalage(
            world, SCENARIO, make_vassal_term(PLAYER, CAUTIOUS_RIVAL), SCENE_ID
        )


def test_pair_at_war_is_rejected() -> None:
    world = make_world()
    set_war_relation(world, PLAYER, CAUTIOUS_RIVAL)

    with pytest.raises(CampaignProgressError):
        sign_vassalage(
            world, SCENARIO, make_vassal_term(PLAYER, CAUTIOUS_RIVAL), SCENE_ID
        )


def test_allied_pair_is_rejected() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)

    with pytest.raises(CampaignProgressError):
        sign_vassalage(
            world, SCENARIO, make_vassal_term(PLAYER, CAUTIOUS_RIVAL), SCENE_ID
        )


def test_vassal_with_an_overlord_cannot_take_a_second() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)

    with pytest.raises(CampaignProgressError):
        sign_vassalage(
            world, SCENARIO, make_vassal_term(WRATHFUL_RIVAL, CAUTIOUS_RIVAL), SCENE_ID
        )


def test_cycle_is_rejected() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    add_vassalage(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    with pytest.raises(CampaignProgressError):
        sign_vassalage(
            world, SCENARIO, make_vassal_term(WRATHFUL_RIVAL, PLAYER), SCENE_ID
        )


def test_legacy_ruleset_rejects_signing() -> None:
    world = make_world()
    world.vassal_ruleset = 0

    with pytest.raises(CampaignProgressError):
        sign_vassalage(
            world, SCENARIO, make_vassal_term(PLAYER, CAUTIOUS_RIVAL), SCENE_ID
        )


def test_terms_card_routes_to_the_vassal_signer() -> None:
    world = make_world()
    card = TermsCard(
        proposer_id=PLAYER,
        counterpart_id=CAUTIOUS_RIVAL,
        terms=[make_vassal_term(PLAYER, CAUTIOUS_RIVAL)],
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )

    apply_terms_card(world, SCENARIO, card, SCENE_ID)

    assert vassalage_of(world, CAUTIOUS_RIVAL) is not None


def test_price_scales_with_percent_and_flat_terms() -> None:
    light = make_vassal_term(PLAYER, CAUTIOUS_RIVAL, tribute=10)
    heavy = tier_term(VassalTier.PUPPET, PLAYER, CAUTIOUS_RIVAL)

    assert vassal_price(light, TUNING) == 10 * TUNING.price_per_tribute_percent + (
        TUNING.price_forever
    )
    assert vassal_price(heavy, TUNING) > vassal_price(light, TUNING)
    assert vassal_price(heavy, TUNING) >= (
        TUNING.price_foreign_policy + TUNING.price_garrison
    )


def test_fixed_duration_is_priced_per_turn() -> None:
    term = make_vassal_term(PLAYER, CAUTIOUS_RIVAL, tribute=0, duration=8)

    assert vassal_price(term, TUNING) == 8 * TUNING.price_per_vassal_turn


def test_defenceless_vassal_accepts_a_light_tributary_and_refuses_a_puppet() -> None:
    world = make_world()
    for army in list(world.armies.values()):
        if army.owner_id == CAUTIOUS_RIVAL:
            del world.armies[army.id]
    light = make_vassal_term(PLAYER, CAUTIOUS_RIVAL, tribute=5, duration=1)
    heavy = tier_term(VassalTier.PUPPET, PLAYER, CAUTIOUS_RIVAL)

    assert does_counterpart_accept_vassalage(world, SCENARIO, light, PLAYER)
    assert not does_counterpart_accept_vassalage(world, SCENARIO, heavy, PLAYER)
