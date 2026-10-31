from app.engine.alliances.answers import apply_answer
from app.engine.alliances.refusal import break_alliance
from app.engine.alliances.registry import alliance_between
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.opinion import opinion_of
from app.engine.pressure.shocks import record_shock
from app.models.orders import AnswerCallOrder, DeclareWarOrder
from app.models.world_alliance import AllianceStanding
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_state import WorldState
from strategy_contracts.alliance import AllianceType
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.enums import RelationStatus
from strategy_contracts.pressure import ShockKind

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_alliance,
    make_world,
)

ALLIANCE = SCENARIO.tuning.alliance
DIPLOMACY = SCENARIO.tuning.diplomacy


def _leader(world: WorldState, faction_id: str):
    return world.leaders[world.factions[faction_id].leader_id]


def _defensive_call_to_player() -> WorldState:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=CAUTIOUS_RIVAL),
    )
    return world


def _refuse(world: WorldState):
    call = world.alliance.calls[0]
    order = AnswerCallOrder(faction_id=PLAYER, call_id=call.id, is_joining=False)
    return apply_answer(world, SCENARIO, order)


def _relation(world: WorldState, first: str, second: str) -> RelationStatus:
    pair = tuple(sorted((first, second)))
    return next(
        item.status
        for item in world.relations
        if (item.faction_a, item.faction_b) == pair
    )


def test_refusal_charges_opinion_more_for_defensive() -> None:
    defensive = _defensive_call_to_player()
    caller = _leader(defensive, CAUTIOUS_RIVAL)
    before = opinion_of(caller, _leader(defensive, PLAYER).id)
    offensive = make_world()
    add_alliance(offensive, WRATHFUL_RIVAL, PLAYER, AllianceType.OFFENSIVE)
    declare_war(
        offensive,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=CAUTIOUS_RIVAL),
    )
    aggressor = _leader(offensive, WRATHFUL_RIVAL)
    before_offensive = opinion_of(aggressor, _leader(offensive, PLAYER).id)

    _refuse(defensive)
    _refuse(offensive)

    after = opinion_of(caller, _leader(defensive, PLAYER).id)
    after_offensive = opinion_of(aggressor, _leader(offensive, PLAYER).id)
    assert before - after == ALLIANCE.refusal_opinion_cost_defensive
    assert before_offensive - after_offensive == ALLIANCE.refusal_opinion_cost_offensive


def test_first_refusal_keeps_the_alliance_and_counts_it() -> None:
    world = _defensive_call_to_player()

    _refuse(world)

    commitment = alliance_between(world, PLAYER, CAUTIOUS_RIVAL)
    assert commitment is not None
    [standing] = world.alliance.standing
    assert standing.refusals_by_faction == {PLAYER: 1}


def test_second_refusal_breaks_alliance_and_charges_the_refuser() -> None:
    world = _defensive_call_to_player()
    commitment = alliance_between(world, PLAYER, CAUTIOUS_RIVAL)
    assert commitment is not None
    world.alliance.standing.append(
        AllianceStanding(alliance_id=commitment.id, refusals_by_faction={PLAYER: 1})
    )
    reputation = world.factions[PLAYER].reputation

    _refuse(world)

    assert commitment.status is CommitmentStatus.BREACHED
    assert _relation(world, PLAYER, CAUTIOUS_RIVAL) == RelationStatus.PEACE
    assert [mark.faction_id for mark in world.oathbreakers] == [PLAYER]
    assert (
        reputation - world.factions[PLAYER].reputation
        == DIPLOMACY.breach_reputation_cost
    )


def test_refusing_ally_facing_destruction_breaks_alliance() -> None:
    world = _defensive_call_to_player()
    commitment = alliance_between(world, PLAYER, CAUTIOUS_RIVAL)
    record_shock(
        world, SCENARIO, ShockKind.CAPITAL_FALLS, CAUTIOUS_RIVAL, world.wars[0].id
    )

    _refuse(world)

    assert commitment is not None
    assert commitment.status is CommitmentStatus.BREACHED


def test_break_defensive_gives_ground_to_ally() -> None:
    world = _defensive_call_to_player()
    record_shock(
        world, SCENARIO, ShockKind.CAPITAL_FALLS, CAUTIOUS_RIVAL, world.wars[0].id
    )

    _refuse(world)

    grounds = [
        (item.holder_faction_id, item.target_faction_id, item.kind)
        for item in world.grounds
    ]
    assert (CAUTIOUS_RIVAL, PLAYER, GroundKind.BROKEN_PROMISE) in grounds


def test_break_offensive_gives_no_ground() -> None:
    world = make_world()
    add_alliance(world, WRATHFUL_RIVAL, PLAYER, AllianceType.OFFENSIVE)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=CAUTIOUS_RIVAL),
    )
    commitment = alliance_between(world, WRATHFUL_RIVAL, PLAYER)
    world.alliance.standing.append(
        AllianceStanding(alliance_id=commitment.id, refusals_by_faction={PLAYER: 1})
    )

    _refuse(world)

    assert commitment.status is CommitmentStatus.BREACHED
    assert world.grounds == []


def test_break_charges_cost_exactly_once() -> None:
    world = _defensive_call_to_player()
    commitment = alliance_between(world, PLAYER, CAUTIOUS_RIVAL)
    record_shock(
        world, SCENARIO, ShockKind.CAPITAL_FALLS, CAUTIOUS_RIVAL, world.wars[0].id
    )
    _refuse(world)
    reputation = world.factions[PLAYER].reputation

    assert break_alliance(world, SCENARIO, PLAYER, commitment) == []
    assert world.factions[PLAYER].reputation == reputation
    assert len(world.oathbreakers) == 1
