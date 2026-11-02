from uuid import UUID

from app.middleware.internal_auth import require_internal_service_token
from app.routers.epilogue import Service, User
from fastapi import APIRouter, Depends
from strategy_contracts.epilogue import (
    EpilogueClaim,
    EpilogueClaimInput,
    EpilogueCompleteInput,
    EpilogueFailInput,
    EpilogueView,
)

router = APIRouter(
    prefix="/internal/v1/playthroughs/{playthrough_id}/epilogue",
    tags=["internal-epilogue"],
    dependencies=[Depends(require_internal_service_token)],
)


@router.post("/claim")
async def claim_epilogue(
    playthrough_id: UUID, request: EpilogueClaimInput, user: User, service: Service
) -> EpilogueClaim:
    """Lease the closing entry only for an independently verified browser owner."""
    return await service.claim(playthrough_id, user.user_id, request.claim_id)


@router.post("/complete")
async def complete_epilogue(
    playthrough_id: UUID, request: EpilogueCompleteInput, user: User, service: Service
) -> EpilogueView:
    """Save the closing entry once using its input hash and live lease token."""
    return await service.complete(playthrough_id, user.user_id, request)


@router.post("/fail")
async def fail_epilogue(
    playthrough_id: UUID, request: EpilogueFailInput, user: User, service: Service
) -> EpilogueView:
    """Record a retryable delivery failure without blocking anything else."""
    return await service.fail(playthrough_id, user.user_id, request)
