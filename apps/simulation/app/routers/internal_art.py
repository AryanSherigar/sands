from typing import Annotated
from uuid import UUID

from app.db.pool import get_connection
from app.middleware.auth import get_current_user
from app.middleware.internal_auth import require_internal_service_token
from app.models.auth import CurrentUser
from app.services.art_service import ArtService
from fastapi import APIRouter, Depends, Path
from psycopg import AsyncConnection
from strategy_contracts.art import (
    ART_ITEM_ID_PATTERN,
    MAX_ART_ITEM_ID_CHARS,
    ArtClaim,
    ArtClaimInput,
    ArtCompleteInput,
    ArtFailInput,
    ArtKind,
    ArtView,
)

router = APIRouter(
    prefix="/internal/v1/playthroughs/{playthrough_id}/art/{kind}/{item_id}",
    tags=["internal-art"],
    dependencies=[Depends(require_internal_service_token)],
)
User = Annotated[CurrentUser, Depends(get_current_user)]
ItemId = Annotated[
    str,
    Path(min_length=1, max_length=MAX_ART_ITEM_ID_CHARS, pattern=ART_ITEM_ID_PATTERN),
]


def get_art_service(
    connection: Annotated[AsyncConnection, Depends(get_connection)],
) -> ArtService:
    return ArtService(connection)


Service = Annotated[ArtService, Depends(get_art_service)]


@router.post("/claim")
async def claim_art(
    playthrough_id: UUID,
    kind: ArtKind,
    item_id: ItemId,
    request: ArtClaimInput,
    user: User,
    service: Service,
) -> ArtClaim:
    """Lease art generation only for an independently verified browser owner."""
    return await service.claim(
        playthrough_id, user.user_id, kind, item_id, request.claim_id
    )


@router.post("/complete")
async def complete_art(
    playthrough_id: UUID,
    kind: ArtKind,
    item_id: ItemId,
    request: ArtCompleteInput,
    user: User,
    service: Service,
) -> ArtView:
    """Save the generated image URL once, fenced by the live lease token."""
    return await service.complete(playthrough_id, user.user_id, kind, item_id, request)


@router.post("/fail")
async def fail_art(
    playthrough_id: UUID,
    kind: ArtKind,
    item_id: ItemId,
    request: ArtFailInput,
    user: User,
    service: Service,
) -> ArtView:
    """Record a retryable generation failure without blocking the campaign."""
    return await service.fail(playthrough_id, user.user_id, kind, item_id, request)
