import pytest
from app.engine.alliances.answers import (
    apply_answer,
    join_score_terms,
    npc_answer,
    resolve_calls,
    validate_answer_call,
)
from app.engine.diplomacy.phase import DiplomacyPhase
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.opinion import opinion_of, shift_opinion
from app.exceptions.command_exceptions import CommandError
from app.models.orders import AnswerCallOrder, DeclareWarOrder
from app.models.world_alliance import CallToArmsState
from app.models.world_diplomacy import WarSide
from app.models.world_state import WorldState
from strategy_contracts.alliance import AllianceType

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_alliance,
    make_world,
)
from tests.engine.diplomacy.builders import queue_npc_order, run_phase, set_traits

TUNING = SCENARIO.tuning.alliance
DOMINATING_OPINION = 400


def _declare(world: WorldState, target: str = PLAYER) -> None:
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=target),
    )


def _at_deadline(world: WorldState) -> None:
    world.clock.turn = world.alliance.calls[0].deadline_turn


def _defensive_world(ally_traits: list[str]) -> WorldState:
    world = make_world()
    set_traits(world, CAUTIOUS_RIVAL, ally_traits)
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    _declare(world)
    return world


def _offensive_world(ally_traits: list[str]) -> WorldState:
    world = make_world()
    set_traits(world, CAUTIOUS_RIVAL, ally_traits)
    add_alliance(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL, AllianceType.OFFENSIVE)
    _declare(world)
    return world


def _kinds(events) -> list[str]:
    return [event.kind for event in events]


def test_high_honor_trust_ally_joins() -> None:
    world = _defensive_world(["honorable", "trusting"])
    _at_deadline(world)

    events = resolve_calls(world, SCENARIO)

    assert CAUTIOUS_RIVAL in world.wars[0].participant_ids
    assert world.alliance.calls == []
    assert "ally_joined" in _kinds(events)


def test_cautious_greedy_ally_refuses() -> None:
    world = _defensive_world(["cautious", "paranoid"])
    _at_deadline(world)

    events = resolve_calls(world, SCENARIO)

    assert CAUTIOUS_RIVAL not in world.wars[0].participant_ids
    assert world.alliance.calls == []
    assert "call_refused" in _kinds(events)


def test_opinion_of_caller_tips_close_call() -> None:
    liked = _offensive_world([])
    shift_opinion(liked, CAUTIOUS_RIVAL, WRATHFUL_RIVAL, "liked", DOMINATING_OPINION, 0)
    disliked = _offensive_world([])
    shift_opinion(
        disliked, CAUTIOUS_RIVAL, WRATHFUL_RIVAL, "disliked", -DOMINATING_OPINION, 0
    )

    assert npc_answer(liked, SCENARIO, liked.alliance.calls[0]).is_joining
    assert not npc_answer(disliked, SCENARIO, disliked.alliance.calls[0]).is_joining


def test_weak_ally_scores_lower_than_a_strong_one() -> None:
    strong = _offensive_world([])
    weak = _offensive_world([])
    for army in weak.armies.values():
        if army.owner_id == CAUTIOUS_RIVAL:
            army.troops = {kind: 0 for kind in army.troops}

    strong_terms = join_score_terms(strong, SCENARIO, strong.alliance.calls[0])
    weak_terms = join_score_terms(weak, SCENARIO, weak.alliance.calls[0])

    assert weak_terms["strength"] < strong_terms["strength"]


def test_defensive_call_scores_the_defensive_bonus() -> None:
    world = _defensive_world([])

    terms = join_score_terms(world, SCENARIO, world.alliance.calls[0])

    assert terms["legitimacy"] == TUNING.join_defensive_bonus


def _player_ally_world() -> WorldState:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    _declare(world, target=CAUTIOUS_RIVAL)
    return world


def test_unanswered_player_call_is_refusal() -> None:
    world = _player_ally_world()
    _at_deadline(world)

    events = resolve_calls(world, SCENARIO)

    assert PLAYER not in world.wars[0].participant_ids
    assert "call_refused" in _kinds(events)


def test_player_join_answer_applied_at_rollover() -> None:
    world = _player_ally_world()
    call = world.alliance.calls[0]
    order = AnswerCallOrder(faction_id=PLAYER, call_id=call.id, is_joining=True)

    events = apply_answer(world, SCENARIO, order)

    assert PLAYER in world.wars[0].participant_ids
    assert world.wars[0].side_by_faction[PLAYER] is WarSide.DEFENDER
    assert world.alliance.calls == []
    assert "ally_joined" in _kinds(events)


def test_player_refusal_answer_refuses() -> None:
    world = _player_ally_world()
    call = world.alliance.calls[0]
    order = AnswerCallOrder(faction_id=PLAYER, call_id=call.id, is_joining=False)

    events = apply_answer(world, SCENARIO, order)

    assert PLAYER not in world.wars[0].participant_ids
    assert "call_refused" in _kinds(events)


def test_second_answer_rejected() -> None:
    world = _player_ally_world()
    call = world.alliance.calls[0]
    order = AnswerCallOrder(faction_id=PLAYER, call_id=call.id, is_joining=True)
    apply_answer(world, SCENARIO, order)

    with pytest.raises(CommandError) as error:
        validate_answer_call(world, order)

    assert error.value.code == "unknown_call"


def test_answer_after_deadline_rejected() -> None:
    world = _player_ally_world()
    call = world.alliance.calls[0]
    world.clock.turn = call.deadline_turn + 1
    order = AnswerCallOrder(faction_id=PLAYER, call_id=call.id, is_joining=True)

    with pytest.raises(CommandError) as error:
        validate_answer_call(world, order)

    assert error.value.code == "call_expired"


def test_non_ally_cannot_answer() -> None:
    world = _player_ally_world()
    order = AnswerCallOrder(
        faction_id=WRATHFUL_RIVAL, call_id=world.alliance.calls[0].id, is_joining=True
    )

    with pytest.raises(CommandError) as error:
        validate_answer_call(world, order)

    assert error.value.code == "not_ally"


def test_both_sides_ally_joins_one_and_pays_cost_to_other() -> None:
    world = make_world()
    set_traits(world, CAUTIOUS_RIVAL, ["honorable", "trusting"])
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    add_alliance(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL, AllianceType.OFFENSIVE)
    _declare(world)
    _at_deadline(world)
    aggressor = world.leaders[world.factions[WRATHFUL_RIVAL].leader_id]
    ally_leader_id = world.factions[CAUTIOUS_RIVAL].leader_id
    before = opinion_of(aggressor, ally_leader_id)

    resolve_calls(world, SCENARIO)

    war = world.wars[0]
    assert war.side_by_faction[CAUTIOUS_RIVAL] is WarSide.DEFENDER
    assert (
        opinion_of(aggressor, ally_leader_id) == before - TUNING.both_sides_opinion_cost
    )
    assert world.alliance.calls == []


def test_npc_answer_is_deterministic_for_same_world() -> None:
    world = _defensive_world(["honorable", "trusting"])
    call: CallToArmsState = world.alliance.calls[0]

    assert npc_answer(world, SCENARIO, call) == npc_answer(
        world.model_copy(deep=True), SCENARIO, call
    )


def test_call_for_an_ended_war_is_dropped() -> None:
    world = _defensive_world(["honorable", "trusting"])
    _at_deadline(world)
    world.wars.clear()

    events = resolve_calls(world, SCENARIO)

    assert world.alliance.calls == []
    assert events == []


def test_queued_player_answer_lands_in_the_diplomacy_phase() -> None:
    world = _player_ally_world()
    call = world.alliance.calls[0]
    queued = queue_npc_order(
        world,
        SCENARIO,
        AnswerCallOrder(faction_id=PLAYER, call_id=call.id, is_joining=True),
    )

    result = run_phase(DiplomacyPhase(), queued)

    assert PLAYER in result.world.wars[0].participant_ids
    assert result.world.alliance.calls == []
