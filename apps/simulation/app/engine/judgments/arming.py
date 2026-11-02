from collections.abc import Sequence
from uuid import NAMESPACE_URL, UUID, uuid5

from app.engine.judgments.eligibility import eligible_subjects
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def judgment_scene_id(world: WorldState, subject_id: str) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"{world.playthrough_id}:judgment:{world.clock.turn}:{subject_id}",
    )


def arm_judgment(
    world: WorldState, scenario: StrategyScenario, events: Sequence[EventLogEntry]
) -> None:
    """Pause planning on one judgment, the first eligible subject, if judgments are on."""
    if (
        not scenario.tuning.judgments.is_enabled
        or world.progress.pending_scene_id is not None
    ):
        return
    subjects = eligible_subjects(world, scenario, events)
    if not subjects:
        return
    pending = subjects[0]
    world.judgment_cooldowns[pending.subject_id] = pending.cooldown_until_turn
    world.progress.pending_scene_id = judgment_scene_id(world, pending.subject_id)
    world.progress.negotiation_counterpart_id = pending.accused_faction_id
    world.progress.pending_judgment = pending
