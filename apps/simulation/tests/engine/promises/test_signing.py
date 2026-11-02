from uuid import UUID

import pytest
from app.engine.negotiation import apply_terms_card
from app.engine.promises.signing import SWORN_PROMISE_MADE, sign_sworn_promise
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import CommitmentStatus
from strategy_contracts.terms import PromiseKind, SwornPromiseTerm, TermsCard

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

SCENE_ID = UUID("55555555-5555-5555-5555-555555555555")


def _term(**overrides: object) -> SwornPromiseTerm:
    fields: dict[str, object] = {
        "promisor_id": PLAYER,
        "beneficiary_id": WRATHFUL_RIVAL,
        "promise": PromiseKind.NEVER_ATTACK_FACTION,
        "duration_turns": 6,
    }
    return SwornPromiseTerm(**(fields | overrides))


def _card(term: SwornPromiseTerm) -> TermsCard:
    return TermsCard(
        proposer_id=term.promisor_id,
        counterpart_id=term.beneficiary_id,
        terms=[term],
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )


def test_signing_records_an_active_commitment_and_a_major_event() -> None:
    world = make_world()
    world.clock.turn = 4

    events = sign_sworn_promise(world, _term(), SCENE_ID)

    commitment = world.commitments[-1]
    assert commitment.status is CommitmentStatus.ACTIVE
    assert (commitment.start_turn, commitment.end_turn) == (4, 10)
    assert commitment.origin_scene_id == SCENE_ID
    assert [(event.kind, event.is_major) for event in events] == [
        (SWORN_PROMISE_MADE, True)
    ]
    assert events[0].cause.subject_ids == [PLAYER, WRATHFUL_RIVAL]


def test_confirmed_card_signs_through_apply_terms_card() -> None:
    world = make_world()

    events = apply_terms_card(world, SCENARIO, _card(_term()), SCENE_ID)

    assert [event.kind for event in events] == [SWORN_PROMISE_MADE]
    assert isinstance(world.commitments[-1].term, SwornPromiseTerm)


def test_unconfirmed_promise_card_is_rejected() -> None:
    world = make_world()
    card = _card(_term()).model_copy(update={"is_confirmed_by_player": False})

    with pytest.raises(CampaignProgressError):
        apply_terms_card(world, SCENARIO, card, SCENE_ID)

    assert world.commitments == []


def test_duplicate_active_promise_does_not_stack() -> None:
    world = make_world()
    sign_sworn_promise(world, _term(), SCENE_ID)

    events = sign_sworn_promise(world, _term(duration_turns=9), SCENE_ID)

    assert events == []
    assert len(world.commitments) == 1


def test_same_promise_to_a_different_beneficiary_is_separate() -> None:
    world = make_world()
    sign_sworn_promise(world, _term(), SCENE_ID)
    sign_sworn_promise(world, _term(beneficiary_id=CAUTIOUS_RIVAL), SCENE_ID)

    assert len(world.commitments) == 2


def test_unknown_faction_raises_invalid_term() -> None:
    world = make_world()

    with pytest.raises(CampaignProgressError) as error:
        sign_sworn_promise(world, _term(beneficiary_id="house_nowhere"), SCENE_ID)

    assert (error.value.code, error.value.status_code) == ("invalid_term", 422)


def test_destroyed_faction_raises_invalid_term() -> None:
    world = make_world()
    world.factions[WRATHFUL_RIVAL].is_destroyed = True

    with pytest.raises(CampaignProgressError) as error:
        sign_sworn_promise(world, _term(), SCENE_ID)

    assert error.value.code == "invalid_term"


def test_never_ally_subject_must_be_a_faction() -> None:
    world = make_world()
    term = _term(promise=PromiseKind.NEVER_ALLY_WITH, subject_id="house_nowhere")

    with pytest.raises(CampaignProgressError):
        sign_sworn_promise(world, term, SCENE_ID)


def test_a_region_promise_signs_for_a_known_region() -> None:
    world = make_world()
    term = _term(promise=PromiseKind.NEVER_OCCUPY_REGION, subject_id="aldgate")

    sign_sworn_promise(world, term, SCENE_ID)

    assert world.commitments[-1].term == term


def test_a_region_promise_for_an_unknown_region_is_rejected() -> None:
    world = make_world()
    term = _term(promise=PromiseKind.NEVER_OCCUPY_REGION, subject_id="nowhere")

    with pytest.raises(CampaignProgressError) as error:
        sign_sworn_promise(world, term, SCENE_ID)

    assert error.value.status_code == 422
