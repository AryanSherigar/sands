from typing import Annotated
from uuid import UUID

from app.middleware.internal_auth import require_internal_service_token
from app.services.api_dependencies import get_scene_exchange_service
from app.services.scene_exchange_service import SceneExchangeService
from fastapi import APIRouter, Depends, Header
from strategy_contracts.scene_exchange import (
    InternalScenePackage,
    LetterBodySubmission,
    SceneExchangeResult,
    SceneExchangeSubmission,
    SceneFailureResult,
)

HEADER_ACTING_USER_ID = "X-Acting-User-Id"

router = APIRouter(
    prefix="/internal/v1/scenes",
    tags=["internal"],
    dependencies=[Depends(require_internal_service_token)],
)
ActingUser = Annotated[UUID, Header(alias=HEADER_ACTING_USER_ID)]
Exchanges = Annotated[SceneExchangeService, Depends(get_scene_exchange_service)]


@router.get("/{scene_id}/package")
async def get_scene_package(
    scene_id: UUID, acting_user_id: ActingUser, service: Exchanges
) -> InternalScenePackage:
    """Return the full scene package for the narrator, after checking the acting owner."""
    return await service.get_package(scene_id, acting_user_id)


@router.post("/{scene_id}/exchanges")
async def submit_scene_exchange(
    scene_id: UUID,
    submission: SceneExchangeSubmission,
    acting_user_id: ActingUser,
    service: Exchanges,
) -> SceneExchangeResult:
    """Record one narrated exchange and the narrator's bounded decision, idempotently."""
    return await service.submit_exchange(scene_id, acting_user_id, submission)


@router.post("/{scene_id}/failures")
async def report_scene_failure(
    scene_id: UUID, acting_user_id: ActingUser, service: Exchanges
) -> SceneFailureResult:
    """Count a failed narration; the third in a row closes the scene with its default outcome."""
    return await service.report_failure(scene_id, acting_user_id)


@router.post("/{scene_id}/letter")
async def store_letter_body(
    scene_id: UUID,
    body: LetterBodySubmission,
    acting_user_id: ActingUser,
    service: Exchanges,
) -> SceneExchangeResult:
    """Store the incoming letter once as the first exchange, so a reopened scene shows the same text."""
    return await service.store_opening_text(scene_id, acting_user_id, body.text)


@router.post("/{scene_id}/opening")
async def store_scene_opening(
    scene_id: UUID,
    body: LetterBodySubmission,
    acting_user_id: ActingUser,
    service: Exchanges,
) -> SceneExchangeResult:
    """Store a letter or judgment scene's opening text once, so a reopened scene shows the same words."""
    return await service.store_opening_text(scene_id, acting_user_id, body.text)
