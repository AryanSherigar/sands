from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user
from app.models.api_battle import CampaignWorldView
from app.models.api_commands import EconomyChoiceRequest
from app.models.auth import CurrentUser
from app.models.battle_progress import MutationResponse, OperationGuard
from app.services.api_dependencies import get_campaign_service, get_world_view_service
from app.services.campaign_service import CampaignService
from app.services.world_view_service import WorldViewService

router = APIRouter(prefix="/v1/playthroughs/{playthrough_id}", tags=["campaign"])
User = Annotated[CurrentUser, Depends(get_current_user)]
Campaign = Annotated[CampaignService, Depends(get_campaign_service)]
World = Annotated[WorldViewService, Depends(get_world_view_service)]


@router.get("/world")
async def get_world(
    playthrough_id: UUID, user: User, service: World
) -> CampaignWorldView:
    """Read the owner's redacted world and current mutation cursor."""
    return await service.load_world(playthrough_id, user.user_id)


@router.post("/end-turn")
async def end_turn(
    playthrough_id: UUID,
    request: OperationGuard,
    user: User,
    service: Campaign,
) -> MutationResponse:
    """Begin campaign resolution from planning, stopping at a battle or scene checkpoint."""
    return await service.begin(playthrough_id, user.user_id, request)


@router.post("/scenes/{scene_id}/choice")
async def choose_economy_outcome(
    playthrough_id: UUID,
    scene_id: UUID,
    request: EconomyChoiceRequest,
    user: User,
    service: Campaign,
) -> MutationResponse:
    """Resolve a code-only treasury shortfall choice exactly once."""
    return await service.choose_economy(playthrough_id, user.user_id, request, scene_id)
