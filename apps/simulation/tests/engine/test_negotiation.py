from uuid import UUID

import pytest
from app.engine import negotiation
from app.engine.negotiation import OfferReaction
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_character import LeaderState, OpinionReason, OpinionState
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_events import PhaseName
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.terms import NonAggressionTerm, TermsCard

from tests.models.builders import make_world

PLAYER = "house_carrow"
RIVAL = "house_ashford"
SCENE_ID = "44444444-4444-4444-4444-444444444444"
TURN = 4
SCENARIO = load_three_crowns()


def _leader(leader_id: str, faction_id: str, traits: list[str]) -> LeaderState:
    return LeaderState(id=leader_id, name=leader_id, faction_id=faction_id, age=40)


def _world(rival_traits: list[str], opinion: int = 0):
    world = make_world()
    world.clock.turn = TURN
    player = _leader("valdren", PLAYER, ["honorable"])
    rival = _leader("mira", RIVAL, rival_traits).model_copy(
        update={
            "trait_ids": rival_traits,
            "opinions": {
                "valdren": OpinionState(
                    target_id="valdren",
                    reasons=[
                        OpinionReason(cause="test", value=opinion, fade_per_turn=0)
                    ],
                )
            },
        }
    )
    world.leaders = {"valdren": player, "mira": rival}
    world.factions[PLAYER].leader_id = "valdren"
    world.factions[RIVAL].leader_id = "mira"
    return world


def _range(world):
    return negotiation.acceptance_range(world, load_three_crowns(), PLAYER, RIVAL)


def test_range_is_ordered_and_deterministic() -> None:
    world = _world(["pragmatic"])
    first, second = _range(world), _range(world)
    assert first == second
    assert first.accept_at >= first.haggle_at


def test_proud_aggressive_leader_demands_more_than_a_cautious_one() -> None:
    wrathful = _range(_world(["wrathful", "proud"]))
    cautious = _range(_world(["cautious", "trusting"]))
    assert wrathful.accept_at > cautious.accept_at


def test_better_opinion_lowers_the_bar() -> None:
    liked = _range(_world(["pragmatic"], opinion=40))
    hated = _range(_world(["pragmatic"], opinion=-40))
    assert liked.accept_at < hated.accept_at


def test_missing_leader_falls_back_to_a_neutral_range() -> None:
    world = _world(["pragmatic"])
    world.factions[RIVAL].leader_id = None
    assert _range(world).accept_at == negotiation.BASE_ACCEPT_THRESHOLD


def test_longer_pacts_are_worth_more_up_to_the_cap() -> None:
    assert negotiation.pact_value(8) > negotiation.pact_value(4)
    assert negotiation.pact_value(99) == negotiation.pact_value(
        negotiation.MAX_PACT_TURNS
    )


@pytest.mark.parametrize(
    ("duration", "expected"),
    [(9, OfferReaction.ACCEPT), (6, OfferReaction.HAGGLE), (2, OfferReaction.REFUSE)],
)
def test_reaction_follows_the_hidden_range(duration, expected) -> None:
    world = _world(["wrathful"])
    assert negotiation.react_to_pact(_range(world), duration) is expected


def _card(duration: int = 6) -> TermsCard:
    return TermsCard(
        proposer_id=PLAYER,
        counterpart_id=RIVAL,
        terms=[
            NonAggressionTerm(
                faction_a=PLAYER, faction_b=RIVAL, duration_turns=duration
            )
        ],
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )


def test_applying_a_pact_records_an_active_commitment() -> None:
    world = _world(["pragmatic"])
    events = negotiation.apply_terms_card(world, SCENARIO, _card(6), SCENE_ID)
    commitment = world.commitments[0]
    assert commitment.status is CommitmentStatus.ACTIVE
    assert (commitment.start_turn, commitment.end_turn) == (TURN, TURN + 6)
    assert str(commitment.origin_scene_id) == SCENE_ID
    assert events[0].phase is PhaseName.DIPLOMACY
    assert events[0].is_major is True


def test_applying_a_pact_is_deterministic_and_numbers_commitments() -> None:
    first, second = _world(["pragmatic"]), _world(["pragmatic"])
    negotiation.apply_terms_card(first, SCENARIO, _card(), SCENE_ID)
    negotiation.apply_terms_card(second, SCENARIO, _card(), SCENE_ID)
    assert first.model_dump() == second.model_dump()
    negotiation.apply_terms_card(first, SCENARIO, _card(), SCENE_ID)
    ids = [commitment.id for commitment in first.commitments]
    assert len(set(ids)) == 2


def test_active_pact_between_two_factions_is_detected_either_way() -> None:
    world = _world(["pragmatic"])
    assert negotiation.has_active_pact(world, PLAYER, RIVAL) is False
    negotiation.apply_terms_card(world, SCENARIO, _card(), SCENE_ID)
    assert negotiation.has_active_pact(world, RIVAL, PLAYER) is True


def test_opening_sets_a_deterministic_pending_scene_without_mutating_the_input() -> (
    None
):
    world = _world(["pragmatic"])
    opened = negotiation.open_negotiation(world, RIVAL, "op-1")
    again = negotiation.open_negotiation(world, RIVAL, "op-1")
    assert world.progress.pending_scene_id is None
    assert opened.progress.pending_scene_id == again.progress.pending_scene_id
    assert opened.progress.pending_scene_id == negotiation.negotiation_scene_id(
        world, "op-1"
    )


def test_opening_is_refused_when_a_scene_is_pending() -> None:
    opened = negotiation.open_negotiation(_world(["pragmatic"]), RIVAL, "op-1")
    with pytest.raises(CampaignProgressError) as error:
        negotiation.open_negotiation(opened, RIVAL, "op-2")
    assert error.value.code == "invalid_lifecycle"


def test_opening_is_refused_during_a_running_campaign() -> None:
    world = _world(["pragmatic"])
    world.progress.phase = PhaseName.MOVEMENT
    with pytest.raises(CampaignProgressError):
        negotiation.open_negotiation(world, RIVAL, "op-1")


@pytest.mark.parametrize("counterpart", [PLAYER, "nobody"])
def test_opening_needs_a_rival_counterpart(counterpart) -> None:
    with pytest.raises(CampaignProgressError) as error:
        negotiation.open_negotiation(_world(["pragmatic"]), counterpart, "op-1")
    assert error.value.code == "invalid_counterpart"


def test_opening_needs_a_counterpart_leader() -> None:
    world = _world(["pragmatic"])
    world.factions[RIVAL].leader_id = None
    with pytest.raises(CampaignProgressError) as error:
        negotiation.open_negotiation(world, RIVAL, "op-1")
    assert error.value.code == "no_leader"


def test_opening_is_refused_while_a_pact_is_active() -> None:
    world = _world(["pragmatic"])
    negotiation.apply_terms_card(world, SCENARIO, _card(), SCENE_ID)
    with pytest.raises(CampaignProgressError) as error:
        negotiation.open_negotiation(world, RIVAL, "op-1")
    assert error.value.code == "pact_exists"


def test_closing_with_a_card_clears_the_scene_and_records_the_pact() -> None:
    opened = negotiation.open_negotiation(_world(["pragmatic"]), RIVAL, "op-1")
    scene_id = opened.progress.pending_scene_id
    closed, events = negotiation.close_negotiation(opened, SCENARIO, scene_id, _card())
    assert closed.progress.pending_scene_id is None
    assert len(closed.commitments) == 1
    assert len(events) == 1
    assert opened.progress.pending_scene_id == scene_id


def test_closing_without_a_card_only_clears_the_scene() -> None:
    opened = negotiation.open_negotiation(_world(["pragmatic"]), RIVAL, "op-1")
    closed, events = negotiation.close_negotiation(
        opened, SCENARIO, opened.progress.pending_scene_id, None
    )
    assert (closed.commitments, events) == ([], [])
    assert closed.progress.pending_scene_id is None


def test_closing_an_unknown_scene_is_refused() -> None:
    opened = negotiation.open_negotiation(_world(["pragmatic"]), RIVAL, "op-1")
    with pytest.raises(CampaignProgressError) as error:
        negotiation.close_negotiation(opened, SCENARIO, UUID(SCENE_ID), None)
    assert error.value.code == "not_found"


@pytest.mark.parametrize(
    "missing_flag", ["is_confirmed_by_player", "is_confirmed_by_counterpart"]
)
def test_a_card_missing_either_confirmation_creates_no_commitment(
    missing_flag: str,
) -> None:
    world = _world(["pragmatic"])
    card = _card(6).model_copy(update={missing_flag: False})
    with pytest.raises(CampaignProgressError):
        negotiation.apply_terms_card(world, SCENARIO, card, SCENE_ID)
    assert world.commitments == []
