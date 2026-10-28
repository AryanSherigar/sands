from uuid import UUID

from app.engine.scene_closing import close_scene
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.battle_progress import OperationGuard
from app.models.persistence import SceneRow
from app.models.replay import ResolveNegotiationReplayInput, ResolveSceneReplayInput
from app.repositories import scene_repo
from app.services.campaign_transaction import CampaignTransition, LockedCampaign
from psycopg import AsyncConnection
from strategy_contracts.scene import (
    RefusedDemand,
    SceneOutcome,
    SceneStatus,
    TermsCardOutcome,
    TermsResult,
)
from strategy_contracts.terms import TermsCard

OPEN_STATUSES = (SceneStatus.PENDING, SceneStatus.OPENED)
REFUSAL_RESULTS = (TermsResult.REFUSED, TermsResult.WALKED_OUT)


async def require_open_scene(
    connection: AsyncConnection, locked: LockedCampaign, scene_id: UUID
) -> SceneRow:
    scene = await scene_repo.get_scene(connection, scene_id)
    is_available = (
        scene is not None
        and scene.playthrough_id == locked.world.playthrough_id
        and scene.status in OPEN_STATUSES
    )
    if scene is None or not is_available:
        raise CampaignProgressError("scene unavailable", "not_found", 404)
    return scene


def build_outcome(result: TermsResult, card: TermsCard | None) -> TermsCardOutcome:
    return TermsCardOutcome(result=result, terms_card=card)


def attach_refused_demand(
    outcome: SceneOutcome,
    status: SceneStatus,
    proposal: TermsCard | None,
    tone_grade: int,
) -> tuple[SceneOutcome, SceneStatus]:
    """Only an explicit refusal or walk-out carries the demand on the table; a defaulted scene never angers anyone."""
    is_refusal = (
        isinstance(outcome, TermsCardOutcome)
        and outcome.result in REFUSAL_RESULTS
        and status == SceneStatus.RESOLVED
    )
    if not is_refusal or proposal is None:
        return outcome, status
    refused = RefusedDemand(terms_card=proposal, tone_grade=tone_grade)
    return outcome.model_copy(update={"refused_demand": refused}), status


def replay_input_for(
    guard: OperationGuard, scene: SceneRow, outcome: SceneOutcome
) -> ResolveNegotiationReplayInput | ResolveSceneReplayInput:
    if isinstance(outcome, TermsCardOutcome):
        return ResolveNegotiationReplayInput(
            guard=guard,
            scene_id=scene.scene_id,
            terms_card=outcome.terms_card,
            result=outcome.result,
            refused_demand=outcome.refused_demand,
        )
    return ResolveSceneReplayInput(
        guard=guard,
        scene_id=scene.scene_id,
        scene_type=scene.scene_type,
        outcome=outcome,
    )


async def close_transition(
    connection: AsyncConnection,
    guard: OperationGuard,
    scene_id: UUID,
    outcome: SceneOutcome,
    status: SceneStatus,
    locked: LockedCampaign,
) -> CampaignTransition:
    scene = await require_open_scene(connection, locked, scene_id)
    world, events = close_scene(
        locked.world,
        locked.playthrough.scenario,
        scene.scene_type,
        scene_id,
        outcome,
    )
    if not await scene_repo.resolve_scene(connection, scene_id, status, outcome):
        raise CampaignProgressError("scene already resolved", "invalid_lifecycle")
    return CampaignTransition(
        world=world,
        events=events,
        replay_input=replay_input_for(guard, scene, outcome),
    )
