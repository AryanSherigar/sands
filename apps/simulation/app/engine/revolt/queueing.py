from app.models.world_events import PendingRevoltTalk
from app.models.world_internal import UprisingState
from app.models.world_state import WorldState


def queue_revolt_talk(world: WorldState, uprising: UprisingState) -> None:
    world.revolt_talk_queue.append(
        PendingRevoltTalk(
            uprising_id=uprising.id,
            region_id=uprising.region_id,
            faction_id=uprising.faction_id,
            archetype=uprising.archetype,
        )
    )


def is_region_locked(world: WorldState, region_id: str) -> bool:
    return world.revolt_lockouts.get(region_id, 0) > world.clock.turn
