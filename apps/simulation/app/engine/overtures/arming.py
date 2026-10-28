from app.engine.negotiation import negotiation_scene_id
from app.engine.overtures.cards import build_overture
from app.engine.overtures.renewals import prune_renewals
from app.engine.overtures.selection import select_overture
from app.models.world_events import PendingNegotiation
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario

OVERTURE_TRIGGER_PREFIX = "overture"


def arm_overture(world: WorldState, scenario: StrategyScenario) -> None:
    """Pause planning on the first NPC approach, if one qualifies this rollover."""
    prune_renewals(world)
    chosen = select_overture(world, scenario)
    if chosen is None:
        return
    faction_id, kind = chosen
    overture = build_overture(world, scenario, faction_id, kind)
    if overture.truce_id in world.overture_renewals:
        world.overture_renewals.remove(overture.truce_id)
    identity = f"{OVERTURE_TRIGGER_PREFIX}_{faction_id}"
    cooldown_until = world.clock.turn + scenario.tuning.overtures.cooldown_turns
    world.overture_cooldowns[faction_id] = cooldown_until
    world.progress.pending_scene_id = negotiation_scene_id(world, identity)
    world.progress.negotiation_counterpart_id = faction_id
    world.progress.pending_negotiation = PendingNegotiation(
        trigger_id=identity,
        initiator_faction_id=faction_id,
        is_declinable=True,
        cooldown_until_turn=cooldown_until,
        overture=overture,
    )
