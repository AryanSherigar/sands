from typing import Annotated
from uuid import UUID

from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.battle_progress import OperationGuard
from app.services.api_dependencies import get_proclamation_scene_service
from app.services.proclamation_scene_service import ProclamationSceneService
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from strategy_contracts.proclamation import (
    ActiveProclamation,
    ProclamationDraft,
    ProclamationScenePackage,
    ProclamationVerdict,
)

router = APIRouter(
    prefix="/v1/playthroughs/{playthrough_id}/proclamation",
    tags=["proclamation-scene"],
)
User = Annotated[CurrentUser, Depends(get_current_user)]
Service = Annotated[ProclamationSceneService, Depends(get_proclamation_scene_service)]


class ProclamationConveneRequest(BaseModel):
    draft: ProclamationDraft
    is_rescinding_previous: bool = False


class ProclamationDecisionRequest(BaseModel):
    guard: OperationGuard
    draft: ProclamationDraft
    verdict: ProclamationVerdict = "fiat"
    is_rescinding_previous: bool = False


@router.post("/convene", response_model=ProclamationScenePackage)
async def convene_proclamation_council(
    playthrough_id: UUID,
    request: ProclamationConveneRequest,
    user: User,
    service: Service,
) -> ProclamationScenePackage:
    """Convene the 4-minister Royal Council for an edict draft."""
    return await service.convene_council(
        playthrough_id=playthrough_id,
        user_id=user.user_id,
        draft=request.draft,
        is_rescinding_previous=request.is_rescinding_previous,
    )


@router.post("/decision", response_model=ActiveProclamation)
async def decide_proclamation_endpoint(
    playthrough_id: UUID,
    request: ProclamationDecisionRequest,
    user: User,
    service: Service,
) -> ActiveProclamation:
    """Commit the proclamation decision (fiat or compromise) and enact the edict."""
    return await service.decide_proclamation(
        playthrough_id=playthrough_id,
        user_id=user.user_id,
        guard=request.guard,
        draft=request.draft,
        verdict=request.verdict,
        is_rescinding_previous=request.is_rescinding_previous,
    )
