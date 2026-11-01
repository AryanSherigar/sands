from typing import Annotated
from uuid import UUID

from app.db.pool import get_connection
from app.middleware.auth import get_current_user
from app.middleware.internal_auth import require_internal_service_token
from app.models.auth import CurrentUser
from app.services.dispatch_service import DispatchService
from fastapi import APIRouter, Depends, Path
from psycopg import AsyncConnection
from strategy_contracts.agents import (
    MAX_RUMOR_ID_CHARS,
    RUMOR_ID_PATTERN,
    DispatchClaim,
    DispatchClaimInput,
    DispatchCompleteInput,
    DispatchFailInput,
    DispatchView,
)

router = APIRouter(
    prefix="/internal/v1/playthroughs/{playthrough_id}/dispatches/{rumor_id}",
    tags=["internal-dispatches"],
    dependencies=[Depends(require_internal_service_token)],
)
User = Annotated[CurrentUser, Depends(get_current_user)]
RumorId = Annotated[
    str, Path(min_length=1, max_length=MAX_RUMOR_ID_CHARS, pattern=RUMOR_ID_PATTERN)
]


def get_dispatch_service(
    connection: Annotated[AsyncConnection, Depends(get_connection)],
) -> DispatchService:
    return DispatchService(connection)


Service = Annotated[DispatchService, Depends(get_dispatch_service)]


@router.post("/claim")
async def claim_dispatch(
    playthrough_id: UUID,
    rumor_id: RumorId,
    request: DispatchClaimInput,
    user: User,
    service: Service,
) -> DispatchClaim:
    """Lease dispatch writing only for an independently verified browser owner."""
    return await service.claim(playthrough_id, user.user_id, rumor_id, request.claim_id)


@router.post("/complete")
async def complete_dispatch(
    playthrough_id: UUID,
    rumor_id: RumorId,
    request: DispatchCompleteInput,
    user: User,
    service: Service,
) -> DispatchView:
    """Save the written dispatch once, fenced by the live lease token."""
    return await service.complete(playthrough_id, user.user_id, rumor_id, request)


@router.post("/fail")
async def fail_dispatch(
    playthrough_id: UUID,
    rumor_id: RumorId,
    request: DispatchFailInput,
    user: User,
    service: Service,
) -> DispatchView:
    """Record a retryable writing failure without blocking the campaign."""
    return await service.fail(playthrough_id, user.user_id, rumor_id, request)
