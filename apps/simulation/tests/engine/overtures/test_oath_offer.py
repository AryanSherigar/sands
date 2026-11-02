from app.engine.negotiation import close_negotiation
from app.engine.opinion import shift_opinion
from app.engine.overtures.arming import arm_overture
from app.engine.overtures.cards import build_overture
from app.engine.overtures.selection import select_overture
from app.engine.promises.signing import sign_sworn_promise
from app.models.world_state import WorldState
from strategy_contracts.overtures import OvertureKind
from strategy_contracts.scene import TermsResult
from strategy_contracts.terms import PromiseKind, SwornPromiseTerm

from tests.engine.overtures.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    scenario_with,
    war_world,
)

WARM_OPINION = 30
COLD_OPINION = 5
OATH_TURNS = 7
OPINION_CAUSE = "shared_feast"


def _warm_world(opinion: int = WARM_OPINION) -> WorldState:
    world = make_world()
    shift_opinion(world, CAUTIOUS_RIVAL, PLAYER, OPINION_CAUSE, opinion, 0)
    return world


def _never_attack(world: WorldState) -> SwornPromiseTerm:
    return SwornPromiseTerm(
        promisor_id=CAUTIOUS_RIVAL,
        beneficiary_id=PLAYER,
        promise=PromiseKind.NEVER_ATTACK_FACTION,
        duration_turns=OATH_TURNS,
    )


def test_a_warm_neighbour_at_peace_offers_an_oath() -> None:
    chosen = select_overture(_warm_world(), SCENARIO)

    assert chosen is not None
    assert chosen[1] is OvertureKind.OATH_OFFER


def test_a_lukewarm_neighbour_offers_nothing() -> None:
    assert select_overture(_warm_world(COLD_OPINION), SCENARIO) is None


def test_no_oath_is_offered_while_an_equal_one_is_in_force() -> None:
    world = _warm_world()
    chosen = select_overture(world, SCENARIO)
    assert chosen is not None
    offerer = chosen[0]
    term = SwornPromiseTerm(
        promisor_id=offerer,
        beneficiary_id=PLAYER,
        promise=PromiseKind.NEVER_ATTACK_FACTION,
        duration_turns=SCENARIO.tuning.overtures.oath_offer_duration_turns,
    )
    sign_sworn_promise(world, term, None)

    assert select_overture(world, SCENARIO) is None


def test_a_realm_at_war_with_the_player_offers_no_oath() -> None:
    world = war_world()
    shift_opinion(world, WRATHFUL_RIVAL, PLAYER, OPINION_CAUSE, WARM_OPINION, 0)
    scenario = scenario_with(peace_offer_min_strain=101, peace_offer_max_will=0)

    chosen = select_overture(world, scenario)

    assert chosen is None or chosen[0] != WRATHFUL_RIVAL


def test_the_card_is_a_never_attack_promise_by_the_npc_to_the_player() -> None:
    scenario = scenario_with(oath_offer_duration_turns=OATH_TURNS)

    overture = build_overture(
        _warm_world(), scenario, CAUTIOUS_RIVAL, OvertureKind.OATH_OFFER
    )

    assert overture.card is not None
    assert overture.card.proposer_id == CAUTIOUS_RIVAL
    assert overture.card.terms == [_never_attack(_warm_world())]
    assert overture.truce_id is None


def test_arming_pauses_planning_on_the_offer_and_accepting_signs_the_oath() -> None:
    world = _warm_world()
    arm_overture(world, SCENARIO)
    pending = world.progress.pending_negotiation
    scene_id = world.progress.pending_scene_id
    assert pending is not None and scene_id is not None
    assert pending.overture is not None
    assert pending.overture.kind is OvertureKind.OATH_OFFER
    card = pending.overture.card.model_copy(
        update={"is_confirmed_by_player": True, "is_confirmed_by_counterpart": True}
    )

    closed, _ = close_negotiation(world, SCENARIO, scene_id, card, TermsResult.AGREED)

    signed = [
        item.term
        for item in closed.commitments
        if isinstance(item.term, SwornPromiseTerm)
    ]
    assert signed and signed[0].beneficiary_id == PLAYER
    assert signed[0].promise is PromiseKind.NEVER_ATTACK_FACTION
