import pytest
from app.engine.diplomacy.validation import validate_diplomacy_order
from app.engine.negotiation import open_negotiation
from app.engine.vassals.commands import apply_vassal_order, validate_vassal_order
from app.engine.vassals.consent import (
    consume_consent,
    expire_consents,
    has_overlord_consent,
)
from app.exceptions.command_exceptions import CampaignProgressError, CommandError
from app.models.orders import CallNegotiationOrder, GrantConsentOrder
from strategy_contracts.vassal import ConsentAction

from tests.engine.alliances.builders import add_alliance
from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    make_world,
)

VALID_TURNS = SCENARIO.tuning.vassal.consent_valid_turns


def _grant(vassalage_id: str, target: str, action=ConsentAction.PACT):
    return GrantConsentOrder(
        faction_id=PLAYER,
        vassalage_id=vassalage_id,
        action=action,
        target_faction_id=target,
    )


def test_uncontrolled_vassal_acts_freely() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, is_controlled=False)

    assert has_overlord_consent(
        world, CAUTIOUS_RIVAL, ConsentAction.DECLARE_WAR, WRATHFUL_RIVAL
    )


def test_faction_without_an_overlord_acts_freely() -> None:
    assert has_overlord_consent(
        make_world(), CAUTIOUS_RIVAL, ConsentAction.DECLARE_WAR, WRATHFUL_RIVAL
    )


def test_controlled_vassal_with_a_player_overlord_needs_a_grant() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, is_controlled=True)
    order = CallNegotiationOrder(
        faction_id=CAUTIOUS_RIVAL, target_faction_id=WRATHFUL_RIVAL
    )

    with pytest.raises(CommandError) as refused:
        validate_diplomacy_order(world, order, SCENARIO)
    assert refused.value.code == "no_overlord_consent"

    apply_vassal_order(world, SCENARIO, _grant(commitment.id, WRATHFUL_RIVAL))
    validate_diplomacy_order(world, order, SCENARIO)


def test_grant_unlocks_one_use_and_is_consumed() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, is_controlled=True)
    apply_vassal_order(world, SCENARIO, _grant(commitment.id, WRATHFUL_RIVAL))

    consume_consent(world, CAUTIOUS_RIVAL, ConsentAction.PACT, WRATHFUL_RIVAL)

    assert not has_overlord_consent(
        world, CAUTIOUS_RIVAL, ConsentAction.PACT, WRATHFUL_RIVAL
    )


def test_expired_consent_is_ignored() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, is_controlled=True)
    apply_vassal_order(world, SCENARIO, _grant(commitment.id, WRATHFUL_RIVAL))
    world.clock.turn += VALID_TURNS

    assert not has_overlord_consent(
        world, CAUTIOUS_RIVAL, ConsentAction.PACT, WRATHFUL_RIVAL
    )
    expire_consents(world)
    assert world.vassal.consents == []


def test_npc_overlord_refuses_war_on_its_own_ally() -> None:
    world = make_world()
    add_vassalage(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL, is_controlled=True)
    add_alliance(world, WRATHFUL_RIVAL, PLAYER)

    assert not has_overlord_consent(
        world, CAUTIOUS_RIVAL, ConsentAction.DECLARE_WAR, PLAYER
    )


def test_npc_overlord_consents_to_a_neutral_target() -> None:
    world = make_world()
    add_vassalage(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL, is_controlled=True)

    assert has_overlord_consent(
        world, CAUTIOUS_RIVAL, ConsentAction.DECLARE_WAR, PLAYER
    )


def test_war_on_the_overlord_is_never_blocked() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, is_controlled=True)

    assert has_overlord_consent(
        world, CAUTIOUS_RIVAL, ConsentAction.DECLARE_WAR, PLAYER
    )


def test_grant_by_a_non_overlord_is_rejected() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, is_controlled=True)
    order = _grant(commitment.id, WRATHFUL_RIVAL).model_copy(
        update={"faction_id": WRATHFUL_RIVAL}
    )

    with pytest.raises(CommandError) as refused:
        validate_vassal_order(world, SCENARIO, order)
    assert refused.value.code == "not_overlord"


def test_controlled_player_vassal_cannot_open_a_scene_with_its_overlords_ally() -> None:
    world = make_world()
    add_vassalage(world, WRATHFUL_RIVAL, PLAYER, is_controlled=True)
    add_alliance(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL)

    with pytest.raises(CampaignProgressError) as refused:
        open_negotiation(world, CAUTIOUS_RIVAL, "op-1")
    assert refused.value.code == "no_overlord_consent"
    open_negotiation(world, WRATHFUL_RIVAL, "op-2")
