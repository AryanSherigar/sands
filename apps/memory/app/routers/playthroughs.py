"""POST /v1/playthroughs/{playthrough_id}/memory/retry. Service-authenticated."""

from typing import Annotated
from uuid import UUID

from app.middleware.service_auth import verify_service_identity
from app.models.retry import RetryMemoryResponse
from app.services.memory_retry_service import (
    MemoryRetryService,
    get_memory_retry_service,
)
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/v1/playthroughs", dependencies=[Depends(verify_service_identity)]
)

HTTP_STATUS_OK = 200


@router.post(
    "/{playthrough_id}/memory/retry",
    response_model=RetryMemoryResponse,
    status_code=HTTP_STATUS_OK,
)
async def retry_memory(
    playthrough_id: UUID,
    service: Annotated[MemoryRetryService, Depends(get_memory_retry_service)],
) -> RetryMemoryResponse:
    """Reset failed extraction batches and skipped embeddings for the playthrough,
    trigger one bounded processing pass, and report the current degraded reasons.

    Returns 409 `not_registered` for an unknown playthrough. Never replays a turn."""
    return await service.retry(playthrough_id)
