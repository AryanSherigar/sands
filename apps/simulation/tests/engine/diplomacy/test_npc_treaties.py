from app.engine.opinion import shift_opinion
from app.models.orders import CallNegotiationOrder
from app.models.world_diplomacy import RelationState, WarState
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.terms import AllianceTerm, NonAggressionTerm, TradeDealTerm

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)
from tests.engine.diplomacy.test_plays import _next_turn, _opened

ATTACKER = WRATHFUL_RIVAL
DEFENDER = CAUTIOUS_RIVAL
TUNING = SCENARIO.tuning.diplomacy


def _warm(world: WorldState, warmth: int) -> None:
    shift_opinion(world, DEFENDER, ATTACKER, "test_warmth", warmth, 0)


def _talks(world: WorldState) -> WorldState:
    call = CallNegotiationOrder(faction_id=ATTACKER, target_faction_id=DEFENDER)
    return _next_turn(_opened(world, call)).world


def _terms(world: WorldState) -> list[type]:
    return [type(item.term) for item in world.commitments]


def _both_fight_the_player(world: WorldState) -> None:
    for rival_id in (ATTACKER, DEFENDER):
        low, high = sorted((rival_id, PLAYER))
        world.relations.append(
            RelationState(
                faction_a=low, faction_b=high, status=RelationStatus.WAR, since_turn=0
            )
        )
        world.wars.append(
            WarState(
                id=f"war_{rival_id}",
                attacker_id=rival_id,
                defender_id=PLAYER,
                started_turn=0,
            )
        )


def test_warm_accepted_talks_sign_a_pact_and_a_trade_deal() -> None:
    world = make_world()
    _warm(world, TUNING.npc_treaty_warmth + 5)

    world = _talks(world)

    assert NonAggressionTerm in _terms(world)
    assert TradeDealTerm in _terms(world)


def test_talks_between_ordinary_rulers_below_the_treaty_warmth_sign_nothing() -> None:
    world = make_world()
    _warm(world, TUNING.npc_treaty_warmth - 5)

    world = _talks(world)

    assert world.commitments == []


def test_warm_rulers_with_a_shared_enemy_ally() -> None:
    world = make_world()
    _both_fight_the_player(world)
    _warm(world, TUNING.npc_alliance_warmth + 5)

    world = _talks(world)

    assert AllianceTerm in _terms(world)
