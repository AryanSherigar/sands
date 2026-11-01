"""POST /v1/ingest/items. Service-authenticated."""

from typing import Annotated

from app.middleware.service_auth import verify_service_identity
from app.models.ingest import IngestRequest, IngestResponse
from app.services.ingest_service import IngestService, get_ingest_service
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/v1/ingest", dependencies=[Depends(verify_service_identity)])

HTTP_STATUS_OK = 200


@router.post("/items", response_model=IngestResponse, status_code=HTTP_STATUS_OK)
async def ingest_items(
    request: IngestRequest,
    service: Annotated[IngestService, Depends(get_ingest_service)],
) -> IngestResponse:
    """Idempotently ingest register, turn and flush items for one playthrough."""
    return await service.ingest_items(request)
