from uuid import UUID

from app.models.world_events import PendingNegotiation
from app.models.world_state import WorldState
from app.repositories import scene_exchange_repo, scene_repo
from app.services.negotiation_scene import (
    build_negotiation_package,
    build_peace_package,
)
from psycopg import AsyncConnection
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import ScenePackage

OVERTURE_FIRST_SEQUENCE = 1


def _build_package(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    pending: PendingNegotiation,
) -> ScenePackage:
    is_war_scene = pending.overture is not None and pending.overture.truce_id is None
    build = build_peace_package if is_war_scene else build_negotiation_package
    return build(world, scenario, scene_id, pending.initiator_faction_id, pending)


async def persist_triggered_scene(
    connection: AsyncConnection, world: WorldState, scenario: StrategyScenario
) -> None:
    """Store the scene for an offer the turn rollover armed; a replayed insert is a no-op."""
    pending = world.progress.pending_negotiation
    scene_id = world.progress.pending_scene_id
    if pending is None or scene_id is None:
        return
    package = _build_package(world, scenario, scene_id, pending)
    await scene_repo.insert_scene(connection, package)
    if pending.overture is not None and pending.overture.card is not None:
        await scene_exchange_repo.insert_exchange(
            connection,
            scene_id,
            OVERTURE_FIRST_SEQUENCE,
            "",
            pending.overture.pretext,
            pending.overture.card,
        )
