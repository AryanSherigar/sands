from uuid import UUID

from app.middleware.internal_auth import require_internal_service_token
from app.routers.summaries import Service, User
from fastapi import APIRouter, Depends
from strategy_contracts.summary import (
    SummaryClaim,
    SummaryClaimInput,
    SummaryCompleteInput,
    SummaryFailInput,
    SummaryView,
)

router = APIRouter(
    prefix="/internal/v1/playthroughs/{playthrough_id}/summaries",
    tags=["internal-summaries"],
    dependencies=[Depends(require_internal_service_token)],
)


@router.post("/{summary_id}/claim")
async def claim_summary(
    playthrough_id: UUID,
    summary_id: UUID,
    request: SummaryClaimInput,
    user: User,
    service: Service,
) -> SummaryClaim:
    """Lease a chronicle only for an independently verified browser owner."""
    return await service.claim(
        playthrough_id, user.user_id, summary_id, request.claim_id
    )


@router.post("/{summary_id}/complete")
async def complete_summary(
    playthrough_id: UUID,
    summary_id: UUID,
    request: SummaryCompleteInput,
    user: User,
    service: Service,
) -> SummaryView:
    """Save bounded prose once using its input hash and live lease token."""
    return await service.complete(playthrough_id, user.user_id, summary_id, request)


@router.post("/{summary_id}/fail")
async def fail_summary(
    playthrough_id: UUID,
    summary_id: UUID,
    request: SummaryFailInput,
    user: User,
    service: Service,
) -> SummaryView:
    """Record retryable delivery failure without blocking the campaign."""
    return await service.fail(playthrough_id, user.user_id, summary_id, request)
