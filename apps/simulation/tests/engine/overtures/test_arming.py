from uuid import UUID

from app.engine.negotiation_triggers import arm_triggered_negotiation
from strategy_contracts.conditions import (
    Comparison,
    ConditionMetric,
    ConditionOperator,
)
from strategy_contracts.negotiation_rules import NegotiationRules, NegotiationTrigger
from strategy_contracts.overtures import OvertureKind

from tests.engine.overtures.builders import (
    CAUTIOUS_RIVAL,
    WRATHFUL_RIVAL,
    scenario_with,
    war_world,
)

COOLDOWN_TURNS = 6


def _exhausted_scenario():
    return scenario_with(peace_offer_min_strain=0, cooldown_turns=COOLDOWN_TURNS)


def test_overture_arms_pending_scene_and_cooldown() -> None:
    world = war_world()

    arm_triggered_negotiation(world, _exhausted_scenario())

    pending = world.progress.pending_negotiation
    assert pending is not None
    assert pending.overture is not None
    assert pending.overture.kind is OvertureKind.PEACE_OFFER
    assert pending.initiator_faction_id == WRATHFUL_RIVAL
    assert pending.is_declinable is True
    assert world.progress.pending_scene_id is not None
    assert world.progress.negotiation_counterpart_id == WRATHFUL_RIVAL
    expected = world.clock.turn + COOLDOWN_TURNS
    assert world.overture_cooldowns[WRATHFUL_RIVAL] == expected
    assert pending.cooldown_until_turn == expected


def test_no_overture_while_scene_pending() -> None:
    world = war_world()
    existing = UUID("55555555-5555-5555-5555-555555555555")
    world.progress.pending_scene_id = existing

    arm_triggered_negotiation(world, _exhausted_scenario())

    assert world.progress.pending_scene_id == existing
    assert world.progress.pending_negotiation is None


def test_authored_trigger_wins_over_overture() -> None:
    world = war_world()
    scenario = _exhausted_scenario()
    trigger = NegotiationTrigger(
        id="authored_offer",
        initiator_faction_id=CAUTIOUS_RIVAL,
        condition=Comparison(
            metric=ConditionMetric.TURN, operator=ConditionOperator.GTE, value=0
        ),
        is_declinable=True,
        cooldown_turns=4,
    )
    scenario = scenario.model_copy(
        update={"negotiation": NegotiationRules(triggers=[trigger])}
    )

    arm_triggered_negotiation(world, scenario)

    pending = world.progress.pending_negotiation
    assert pending is not None
    assert pending.trigger_id == "authored_offer"
    assert pending.overture is None


def test_second_arming_during_cooldown_does_nothing() -> None:
    world = war_world()
    scenario = _exhausted_scenario()
    arm_triggered_negotiation(world, scenario)
    world.progress.pending_scene_id = None
    world.progress.pending_negotiation = None

    arm_triggered_negotiation(world, scenario)

    assert world.progress.pending_negotiation is None
