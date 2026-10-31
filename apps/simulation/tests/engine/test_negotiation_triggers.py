import pytest
from app.engine import negotiation
from app.engine.conditions import evaluate
from app.engine.hashing import canonical_world_json
from app.engine.negotiation_triggers import (
    arm_triggered_negotiation,
    firing_triggers,
)
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_character import LeaderState
from app.models.world_diplomacy import CommitmentState
from strategy_contracts.conditions import (
    AllOf,
    Comparison,
    ConditionMetric,
    ConditionOperator,
    Negation,
)
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.negotiation_rules import NegotiationRules, NegotiationTrigger
from strategy_contracts.terms import NonAggressionTerm

from tests.models.builders import make_world

PLAYER = "house_carrow"
RIVAL = "house_ashford"
TRIGGER_TURN = 3
COOLDOWN_TURNS = 4
SCENE_ID = "55555555-5555-5555-5555-555555555555"


def _turn_at_least(value: int) -> Comparison:
    return Comparison(
        metric=ConditionMetric.TURN, operator=ConditionOperator.GTE, value=value
    )


def _scenario(is_declinable: bool = True, condition=None):
    scenario = load_three_crowns()
    trigger = NegotiationTrigger(
        id="ashford_offer",
        initiator_faction_id=RIVAL,
        condition=condition or _turn_at_least(TRIGGER_TURN),
        is_declinable=is_declinable,
        cooldown_turns=COOLDOWN_TURNS,
    )
    scenario.negotiation = NegotiationRules(triggers=[trigger])
    return scenario


def _world(turn: int = TRIGGER_TURN):
    world = make_world()
    world.clock.turn = turn
    world.leaders = {
        "valdren": LeaderState(id="valdren", name="Valdren", faction_id=PLAYER, age=40),
        "mira": LeaderState(id="mira", name="Mira", faction_id=RIVAL, age=40),
    }
    world.factions[PLAYER].leader_id = "valdren"
    world.factions[RIVAL].leader_id = "mira"
    return world


def test_conditions_combine_with_all_of_and_not() -> None:
    world = _world(turn=5)
    condition = AllOf(
        conditions=[_turn_at_least(5), Negation(condition=_turn_at_least(6))]
    )
    assert evaluate(world, condition)
    assert not evaluate(_world(turn=6), condition)


def test_trigger_does_not_fire_before_its_condition_holds() -> None:
    assert firing_triggers(_world(turn=TRIGGER_TURN - 1), _scenario()) == []


def test_firing_trigger_arms_a_pending_offer_and_pauses_planning() -> None:
    world = _world()
    arm_triggered_negotiation(world, _scenario(is_declinable=False))
    assert world.progress.pending_scene_id is not None
    pending = world.progress.pending_negotiation
    assert pending is not None
    assert pending.initiator_faction_id == RIVAL
    assert pending.is_declinable is False
    assert pending.cooldown_until_turn == TRIGGER_TURN + COOLDOWN_TURNS
    with pytest.raises(CampaignProgressError):
        negotiation.require_no_open_negotiation(world)


def test_arming_is_deterministic() -> None:
    first, second = _world(), _world()
    arm_triggered_negotiation(first, _scenario())
    arm_triggered_negotiation(second, _scenario())
    assert canonical_world_json(first) == canonical_world_json(second)


def test_active_pact_blocks_the_trigger() -> None:
    world = _world()
    world.commitments.append(
        CommitmentState(
            id="commitment_1",
            term=NonAggressionTerm(faction_a=PLAYER, faction_b=RIVAL, duration_turns=5),
            start_turn=1,
            end_turn=TRIGGER_TURN + 5,
            origin_scene_id=SCENE_ID,
        )
    )
    assert firing_triggers(world, _scenario()) == []


def test_closing_records_the_cooldown_and_clears_the_offer() -> None:
    world = _world()
    arm_triggered_negotiation(world, _scenario())
    scene_id = world.progress.pending_scene_id
    closed, _ = negotiation.close_negotiation(world, _scenario(), scene_id, None)
    assert closed.progress.pending_negotiation is None
    assert closed.negotiation_cooldowns == {
        "ashford_offer": TRIGGER_TURN + COOLDOWN_TURNS
    }
    closed.clock.turn = TRIGGER_TURN + 1
    assert firing_triggers(closed, _scenario()) == []
    closed.clock.turn = TRIGGER_TURN + COOLDOWN_TURNS
    assert len(firing_triggers(closed, _scenario())) == 1


def test_world_without_offers_serializes_like_before() -> None:
    document = canonical_world_json(_world())
    assert "negotiation_cooldowns" not in document
    assert "pending_negotiation" not in document


def test_authored_weights_change_the_acceptance_range() -> None:
    scenario = load_three_crowns()
    world = _world()
    default = negotiation.acceptance_range(world, scenario, PLAYER, RIVAL)
    scenario.negotiation = NegotiationRules(base_accept=default.accept_at + 10)
    raised = negotiation.acceptance_range(world, scenario, PLAYER, RIVAL)
    assert raised.accept_at == default.accept_at + 10
