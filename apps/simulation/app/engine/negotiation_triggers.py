from app.engine.conditions import evaluate
from app.engine.negotiation import (
    has_active_pact,
    negotiation_scene_id,
    player_faction_id,
)
from app.engine.overtures.arming import arm_overture
from app.models.world_events import PendingNegotiation
from app.models.world_state import WorldState
from strategy_contracts.negotiation_rules import NegotiationTrigger
from strategy_contracts.scenario import StrategyScenario

TRIGGER_OPERATION_PREFIX = "trigger"


def _is_trigger_available(world: WorldState, trigger: NegotiationTrigger) -> bool:
    initiator = world.factions.get(trigger.initiator_faction_id)
    if initiator is None or initiator.is_player or initiator.is_destroyed:
        return False
    if initiator.leader_id is None or initiator.leader_id not in world.leaders:
        return False
    if world.negotiation_cooldowns.get(trigger.id, 0) > world.clock.turn:
        return False
    return not has_active_pact(
        world, player_faction_id(world), trigger.initiator_faction_id
    )


def firing_triggers(
    world: WorldState, scenario: StrategyScenario
) -> list[NegotiationTrigger]:
    return [
        trigger
        for trigger in scenario.negotiation.triggers
        if _is_trigger_available(world, trigger) and evaluate(world, trigger.condition)
    ]


def arm_triggered_negotiation(world: WorldState, scenario: StrategyScenario) -> None:
    """Pause planning on the first firing trigger in authored order, else on an NPC overture."""
    if world.progress.pending_scene_id is not None:
        return
    firing = firing_triggers(world, scenario)
    if not firing:
        arm_overture(world, scenario)
        return
    trigger = firing[0]
    world.progress.pending_scene_id = negotiation_scene_id(
        world, f"{TRIGGER_OPERATION_PREFIX}:{trigger.id}"
    )
    world.progress.negotiation_counterpart_id = trigger.initiator_faction_id
    world.progress.pending_negotiation = PendingNegotiation(
        trigger_id=trigger.id,
        initiator_faction_id=trigger.initiator_faction_id,
        is_declinable=trigger.is_declinable,
        cooldown_until_turn=world.clock.turn + trigger.cooldown_turns,
    )
