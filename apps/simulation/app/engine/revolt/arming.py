from uuid import NAMESPACE_URL, UUID, uuid5

from app.models.world_events import PendingRevoltTalk
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def revolt_scene_id(world: WorldState, region_id: str) -> UUID:
    return uuid5(
        NAMESPACE_URL, f"{world.playthrough_id}:revolt:{world.clock.turn}:{region_id}"
    )


def _is_still_holder(world: WorldState, pending: PendingRevoltTalk) -> bool:
    region = world.regions.get(pending.region_id)
    faction = world.factions.get(pending.faction_id)
    return (
        region is not None
        and region.owner_id == pending.faction_id
        and faction is not None
        and not faction.is_destroyed
    )


def arm_revolt_talk(world: WorldState, scenario: StrategyScenario) -> None:
    """Open the next queued talk as a scene at turn rollover; talks whose region changed hands lapse."""
    if (
        not scenario.tuning.revolt_talk.is_enabled
        or world.progress.pending_scene_id is not None
    ):
        return
    while world.revolt_talk_queue:
        pending = world.revolt_talk_queue.pop(0)
        if not _is_still_holder(world, pending):
            continue
        world.progress.pending_scene_id = revolt_scene_id(world, pending.region_id)
        world.progress.negotiation_counterpart_id = pending.faction_id
        world.progress.pending_revolt_talk = pending
        return
