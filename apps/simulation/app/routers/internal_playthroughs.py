from typing import Annotated

from app.middleware.internal_auth import require_internal_service_token
from app.models.battle_progress import InitializeCampaign, MutationResponse
from app.services.api_dependencies import get_campaign_service
from app.services.campaign_service import CampaignService
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/internal/v1/playthroughs",
    tags=["internal"],
    dependencies=[Depends(require_internal_service_token)],
)


@router.post("")
async def initialize_playthrough(
    request: InitializeCampaign,
    service: Annotated[CampaignService, Depends(get_campaign_service)],
) -> MutationResponse:
    """Validate and initialize a campaign atomically after service authentication."""
    return await service.initialize(request)
