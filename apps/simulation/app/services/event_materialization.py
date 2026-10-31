from app.models.world_state import WorldState
from app.repositories.event_delivery_repo import EventDeliveryRepo
from psycopg import AsyncConnection


async def persist_event_deliveries(
    connection: AsyncConnection, world: WorldState, previous: WorldState
) -> None:
    if not world.pending_event_deliveries:
        return
    repo = EventDeliveryRepo()
    existing = {item.id for item in previous.pending_events}
    for briefing in world.pending_event_deliveries:
        if briefing.event_id not in existing:
            await repo.insert_pending(
                connection,
                world.playthrough_id,
                briefing.event_id,
                world.clock.turn,
                briefing,
            )
