import pytest
from app.engine.alliances.acceptance import does_counterpart_accept_alliance
from app.engine.alliances.pricing import alliance_price
from app.engine.alliances.registry import alliance_between
from app.engine.alliances.signing import sign_alliance
from app.engine.negotiation import apply_terms_card
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import CommitmentStatus
from strategy_contracts.alliance import AllianceTuning, AllianceType
from strategy_contracts.enums import RelationStatus
from strategy_contracts.terms import TermsCard

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    SCENE_ID,
    WRATHFUL_RIVAL,
    add_alliance,
    make_alliance_term,
    make_world,
    set_war_relation,
)

TUNING = AllianceTuning()
FIXED_TURNS = 10
UNREACHABLE_LINE = 10_000


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


def test_sign_creates_commitment_and_relation() -> None:
    world = make_world()
    term = make_alliance_term(PLAYER, CAUTIOUS_RIVAL)

    events = sign_alliance(world, SCENARIO, term, SCENE_ID)

    assert alliance_between(world, PLAYER, CAUTIOUS_RIVAL) is not None
    assert _relation_status(world, PLAYER, CAUTIOUS_RIVAL) == RelationStatus.ALLIANCE
    assert [event.kind for event in events] == ["alliance_signed"]


def test_forever_has_no_end_turn() -> None:
    world = make_world()

    commitment = add_alliance(world, PLAYER, CAUTIOUS_RIVAL, duration_turns=0)

    assert commitment.end_turn is None


def test_fixed_duration_sets_end_turn() -> None:
    world = make_world()

    commitment = add_alliance(world, PLAYER, CAUTIOUS_RIVAL, duration_turns=8)

    assert commitment.end_turn == world.clock.turn + 8
    assert commitment.status is CommitmentStatus.ACTIVE


def test_self_alliance_rejected() -> None:
    world = make_world()

    with pytest.raises(CampaignProgressError) as error:
        sign_alliance(world, SCENARIO, make_alliance_term(PLAYER, PLAYER), SCENE_ID)

    assert error.value.code == "invalid_term"


def test_unknown_or_destroyed_faction_rejected() -> None:
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].is_destroyed = True

    for other in ("house_nowhere", CAUTIOUS_RIVAL):
        with pytest.raises(CampaignProgressError):
            sign_alliance(world, SCENARIO, make_alliance_term(PLAYER, other), SCENE_ID)

    assert world.commitments == []


def test_duplicate_active_alliance_rejected() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)

    with pytest.raises(CampaignProgressError):
        add_alliance(world, CAUTIOUS_RIVAL, PLAYER)

    assert len(world.commitments) == 1


def test_alliance_between_belligerents_rejected() -> None:
    world = make_world()
    set_war_relation(world, PLAYER, CAUTIOUS_RIVAL)

    with pytest.raises(CampaignProgressError):
        add_alliance(world, PLAYER, CAUTIOUS_RIVAL)


def test_price_scales_with_duration_type_and_clause() -> None:
    fixed = make_alliance_term(PLAYER, CAUTIOUS_RIVAL, duration_turns=FIXED_TURNS)
    forever = make_alliance_term(PLAYER, CAUTIOUS_RIVAL)
    loaded = make_alliance_term(
        PLAYER,
        CAUTIOUS_RIVAL,
        alliance_type=AllianceType.OFFENSIVE,
        is_separate_peace_banned=True,
    )

    assert alliance_price(fixed, TUNING) == FIXED_TURNS * TUNING.price_per_alliance_turn
    assert alliance_price(forever, TUNING) == TUNING.price_forever
    assert alliance_price(loaded, TUNING) == (
        TUNING.price_forever
        + TUNING.price_offensive_extra
        + TUNING.price_no_separate_peace_extra
    )


def test_counterpart_accepts_within_acceptance_range() -> None:
    world = make_world()
    term = make_alliance_term(PLAYER, CAUTIOUS_RIVAL)
    scenario = SCENARIO.model_copy(deep=True)

    scenario.negotiation.base_accept = -UNREACHABLE_LINE
    assert does_counterpart_accept_alliance(world, scenario, term, PLAYER)
    scenario.negotiation.base_accept = UNREACHABLE_LINE
    assert not does_counterpart_accept_alliance(world, scenario, term, PLAYER)


def test_confirmed_alliance_card_is_applied_by_the_terms_card_path() -> None:
    world = make_world()
    card = TermsCard(
        proposer_id=PLAYER,
        counterpart_id=CAUTIOUS_RIVAL,
        terms=[make_alliance_term(PLAYER, CAUTIOUS_RIVAL)],
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )

    apply_terms_card(world, SCENARIO, card, SCENE_ID)

    assert alliance_between(world, PLAYER, CAUTIOUS_RIVAL) is not None


def test_legacy_world_without_ruleset_signs_nothing() -> None:
    world = make_world()
    world.alliance_ruleset = 0

    with pytest.raises(CampaignProgressError):
        add_alliance(world, PLAYER, WRATHFUL_RIVAL)
