from uuid import UUID

from app.engine.diplomacy.plays import open_play
from app.engine.negotiation import close_negotiation
from app.engine.outrage.demands import react_to_demand
from app.engine.outrage.status import outrage_of
from app.models.orders import DiplomaticPlayOrder
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.scene import OutrageLevel, RefusedDemand, TermsResult
from strategy_contracts.terms import NonAggressionTerm, PayGoldTerm, TermsCard

from tests.engine.outrage.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_axes,
)

HUGE_DEMAND = 10_000
NEUTRAL_AXES = {"pride": 0, "aggression": 0, "caution": 0}


def _demand(payer_id: str, payee_id: str, amount: int = HUGE_DEMAND) -> TermsCard:
    return TermsCard(
        proposer_id=payee_id,
        counterpart_id=payer_id,
        terms=[PayGoldTerm(payer_id=payer_id, payee_id=payee_id, amount=amount)],
    )


def test_a_refused_overreach_angers_the_ruler_who_was_squeezed() -> None:
    world = make_world()
    scenario = set_axes(world, SCENARIO, WRATHFUL_RIVAL, **NEUTRAL_AXES)

    react_to_demand(
        world,
        scenario,
        demander_id=PLAYER,
        card=_demand(WRATHFUL_RIVAL, PLAYER),
        tone_grade=None,
    )

    state = outrage_of(world, WRATHFUL_RIVAL)
    assert state is not None
    assert state.level == OutrageLevel.ENRAGED
    assert state.target_faction_id == PLAYER


def test_a_modest_ask_offends_nobody() -> None:
    world = make_world()
    scenario = set_axes(world, SCENARIO, WRATHFUL_RIVAL, **NEUTRAL_AXES)

    react_to_demand(
        world,
        scenario,
        demander_id=PLAYER,
        card=_demand(WRATHFUL_RIVAL, PLAYER, amount=1),
        tone_grade=None,
    )

    assert outrage_of(world, WRATHFUL_RIVAL) is None


def test_a_card_that_only_gives_asks_nothing() -> None:
    world = make_world()

    react_to_demand(
        world,
        SCENARIO,
        demander_id=PLAYER,
        card=_demand(PLAYER, WRATHFUL_RIVAL),
        tone_grade=None,
    )

    assert world.outrage == []


def test_the_players_tone_is_recorded_on_their_profile() -> None:
    world = make_world()

    react_to_demand(
        world,
        SCENARIO,
        demander_id=PLAYER,
        card=_demand(WRATHFUL_RIVAL, PLAYER),
        tone_grade=4,
    )

    assert world.player_profile.tone_grade_total == 4
    assert world.player_profile.tone_grade_count == 1


def test_an_npc_overreaching_against_the_player_gives_the_player_a_ground() -> None:
    world = make_world()

    react_to_demand(
        world,
        SCENARIO,
        demander_id=WRATHFUL_RIVAL,
        card=_demand(PLAYER, WRATHFUL_RIVAL),
        tone_grade=None,
    )

    insults = [ground for ground in world.grounds if ground.kind == GroundKind.INSULT]
    assert [ground.holder_faction_id for ground in insults] == [PLAYER]
    assert world.outrage == []


SCENE_ID = UUID("00000000-0000-0000-0000-000000000009")


def _scene_world() -> WorldState:
    world = make_world()
    world.progress.pending_scene_id = SCENE_ID
    world.progress.negotiation_counterpart_id = WRATHFUL_RIVAL
    return world


def test_closing_a_refused_scene_angers_the_ruler_who_refused() -> None:
    refused = RefusedDemand(terms_card=_demand(WRATHFUL_RIVAL, PLAYER), tone_grade=5)

    closed, _ = close_negotiation(
        _scene_world(),
        SCENARIO,
        SCENE_ID,
        None,
        TermsResult.REFUSED,
        refused_demand=refused,
    )

    assert outrage_of(closed, WRATHFUL_RIVAL) is not None


def test_an_agreed_scene_angers_nobody() -> None:
    card = TermsCard(
        proposer_id=PLAYER,
        counterpart_id=WRATHFUL_RIVAL,
        terms=[
            NonAggressionTerm(
                faction_a=PLAYER, faction_b=WRATHFUL_RIVAL, duration_turns=5
            )
        ],
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )
    refused = RefusedDemand(terms_card=_demand(WRATHFUL_RIVAL, PLAYER))

    closed, _ = close_negotiation(
        _scene_world(),
        SCENARIO,
        SCENE_ID,
        card,
        TermsResult.AGREED,
        refused_demand=refused,
    )

    assert closed.outrage == []


def _play_order(demander_id: str, target_id: str, amount: int) -> DiplomaticPlayOrder:
    return DiplomaticPlayOrder(
        faction_id=demander_id,
        target_faction_id=target_id,
        demands=[PayGoldTerm(payer_id=target_id, payee_id=demander_id, amount=amount)],
    )


def test_an_npc_demand_play_against_the_player_earns_the_player_a_ground() -> None:
    world = make_world()

    open_play(world, SCENARIO, _play_order(WRATHFUL_RIVAL, PLAYER, HUGE_DEMAND))

    assert any(ground.kind == GroundKind.INSULT for ground in world.grounds)


def test_an_npc_demand_play_against_another_npc_angers_it() -> None:
    world = make_world()
    scenario = set_axes(world, SCENARIO, CAUTIOUS_RIVAL, **NEUTRAL_AXES)

    events = open_play(
        world, scenario, _play_order(WRATHFUL_RIVAL, CAUTIOUS_RIVAL, HUGE_DEMAND)
    )

    assert outrage_of(world, CAUTIOUS_RIVAL) is not None
    assert "outrage_raised" in [event.kind for event in events]


def test_a_demand_play_without_terms_angers_nobody() -> None:
    world = make_world()
    order = DiplomaticPlayOrder(faction_id=PLAYER, target_faction_id=WRATHFUL_RIVAL)

    open_play(world, SCENARIO, order)

    assert world.outrage == []
