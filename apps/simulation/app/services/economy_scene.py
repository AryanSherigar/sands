from uuid import NAMESPACE_URL, UUID, uuid5

from app.engine.economy.reasons import SHORTFALL_DEFAULT, SHORTFALL_TAKE_LOAN
from app.engine.phases import ScenePause
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_events import PhaseName
from app.models.world_state import WorldState
from app.repositories import scene_repo
from app.services.scene_package_validation import require_valid_package
from psycopg import AsyncConnection
from strategy_contracts.scene import (
    ChoiceOption,
    ChoiceOutcome,
    ChoiceSpec,
    ScenePackage,
    SceneSituation,
    SceneStatus,
)


def economy_package(
    world: WorldState, pause: ScenePause, operation_id: str
) -> ScenePackage:
    identity = uuid5(
        NAMESPACE_URL,
        f"{world.playthrough_id}:economy:{world.clock.turn}:{operation_id}",
    )
    package = ScenePackage(
        scene_id=identity,
        playthrough_id=world.playthrough_id,
        turn=world.clock.turn,
        scene_type=pause.scene_type,
        situation=SceneSituation(summary="Choose how to cover the treasury shortfall."),
        allowed_outcomes=[
            ChoiceSpec(
                options=[
                    ChoiceOption(id=SHORTFALL_TAKE_LOAN, label="Take a loan"),
                    ChoiceOption(id=SHORTFALL_DEFAULT, label="Declare default"),
                ]
            )
        ],
        exchange_cap=0,
        default_outcome=ChoiceOutcome(option_id=SHORTFALL_DEFAULT),
    )
    return require_valid_package(package)


async def persist_pause(
    connection: AsyncConnection,
    world: WorldState,
    pause: ScenePause | None,
    operation_id: str,
) -> None:
    if pause is None:
        return
    if world.progress.phase != PhaseName.ECONOMY:
        raise CampaignProgressError("unsupported campaign scene", "invalid_lifecycle")
    package = economy_package(world, pause, operation_id)
    await scene_repo.insert_scene(connection, package)
    world.progress.pending_scene_id = package.scene_id


async def resolve_economy_choice(
    connection: AsyncConnection, world: WorldState, scene_id: UUID, choice: str
) -> ChoiceOutcome:
    scene = await scene_repo.get_scene(connection, scene_id)
    if (
        world.progress.phase != PhaseName.ECONOMY
        or world.progress.pending_scene_id != scene_id
        or scene is None
        or scene.playthrough_id != world.playthrough_id
    ):
        raise CampaignProgressError("scene unavailable", "not_found", 404)
    if choice not in (SHORTFALL_TAKE_LOAN, SHORTFALL_DEFAULT):
        raise CampaignProgressError("invalid economy choice", "invalid_choice", 422)
    outcome = ChoiceOutcome(option_id=choice)
    if not await scene_repo.resolve_scene(
        connection, scene_id, SceneStatus.RESOLVED, outcome
    ):
        raise CampaignProgressError("scene already resolved", "invalid_lifecycle")
    return outcome
