from typing import Annotated
from uuid import UUID

from app.middleware.auth import get_current_user
from app.models.api_scenes import (
    OpenNegotiationRequest,
    SceneDecisionRequest,
    SceneView,
)
from app.models.auth import CurrentUser
from app.models.battle_progress import MutationResponse
from app.services.api_dependencies import get_negotiation_service
from app.services.negotiation_service import NegotiationService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/v1/playthroughs/{playthrough_id}/scenes", tags=["scenes"])
User = Annotated[CurrentUser, Depends(get_current_user)]
Negotiation = Annotated[NegotiationService, Depends(get_negotiation_service)]


@router.post("/negotiation")
async def open_negotiation(
    playthrough_id: UUID,
    request: OpenNegotiationRequest,
    user: User,
    service: Negotiation,
) -> MutationResponse:
    """Open a non-aggression negotiation with a rival faction and pause the turn on it."""
    return await service.open(playthrough_id, user.user_id, request)


@router.get("/{scene_id}")
async def get_scene(
    playthrough_id: UUID, scene_id: UUID, user: User, service: Negotiation
) -> SceneView:
    """Read the owner-safe scene and transcript, used to reopen it after a refresh."""
    return await service.get_view(playthrough_id, user.user_id, scene_id)


@router.post("/{scene_id}/decision")
async def decide_scene(
    playthrough_id: UUID,
    scene_id: UUID,
    request: SceneDecisionRequest,
    user: User,
    service: Negotiation,
) -> MutationResponse:
    """Confirm the pending terms card, or decline or abandon the negotiation."""
    return await service.decide(playthrough_id, user.user_id, scene_id, request)
