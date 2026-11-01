"""POST /v1/jobs/process-pending. Service-authenticated."""

from typing import Annotated

from app.middleware.service_auth import verify_service_identity
from app.models.process_pending import ProcessPendingRequest, ProcessPendingResponse
from app.services.indexing_service import IndexingService, get_indexing_service
from fastapi import APIRouter, Body, Depends

router = APIRouter(prefix="/v1/jobs", dependencies=[Depends(verify_service_identity)])

HTTP_STATUS_OK = 200


@router.post(
    "/process-pending",
    response_model=ProcessPendingResponse,
    status_code=HTTP_STATUS_OK,
)
async def process_pending(
    service: Annotated[IndexingService, Depends(get_indexing_service)],
    request: Annotated[ProcessPendingRequest | None, Body()] = None,
) -> ProcessPendingResponse:
    """Idempotently process pending embeddings for spans and facts.

    With no request body, performs a global sweep with default deadline.
    With a request body, may scope to a playthrough_id and override deadline_seconds.
    Never raises for embedding-provider failures; they are reported in the response."""
    return await service.process_pending(request)
