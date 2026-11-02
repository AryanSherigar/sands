from uuid import UUID

from app.models.world_events import PendingNegotiation
from app.models.world_state import WorldState
from app.repositories import scene_exchange_repo, scene_repo
from app.services.judgment_scene import build_judgment_package
from app.services.letter_scene import build_letter_package
from app.services.negotiation_scene import (
    build_negotiation_package,
    build_peace_package,
)
from app.services.revolt_scene import build_revolt_talk_package
from psycopg import AsyncConnection
from strategy_contracts.overtures import OvertureKind
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import ScenePackage

OVERTURE_FIRST_SEQUENCE = 1


def _build_package(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    pending: PendingNegotiation,
) -> ScenePackage:
    overture = pending.overture
    is_war_scene = (
        overture is not None
        and overture.truce_id is None
        and overture.kind is not OvertureKind.OATH_OFFER
    )
    build = build_peace_package if is_war_scene else build_negotiation_package
    return build(world, scenario, scene_id, pending.initiator_faction_id, pending)


async def persist_triggered_scene(
    connection: AsyncConnection, world: WorldState, scenario: StrategyScenario
) -> None:
    """Store the scene for an offer the turn rollover armed; a replayed insert is a no-op."""
    pending = world.progress.pending_negotiation
    scene_id = world.progress.pending_scene_id
    if scene_id is not None and world.progress.pending_judgment is not None:
        package = build_judgment_package(
            world, scenario, scene_id, world.progress.pending_judgment
        )
        await scene_repo.insert_scene(connection, package)
        return
    if scene_id is not None and world.progress.pending_revolt_talk is not None:
        package = build_revolt_talk_package(
            world, scenario, scene_id, world.progress.pending_revolt_talk
        )
        await scene_repo.insert_scene(connection, package)
        return
    if scene_id is not None and world.progress.pending_letter is not None:
        package = build_letter_package(
            world, scenario, scene_id, world.progress.pending_letter
        )
        await scene_repo.insert_scene(connection, package)
        return
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
