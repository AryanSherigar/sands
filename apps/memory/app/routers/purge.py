"""POST /v1/purge and GET /v1/scopes. Service-authenticated."""

from typing import Annotated

from app.middleware.service_auth import verify_service_identity
from app.models.purge import PurgeRequest, PurgeResponse, ScopesResponse
from app.services.purge_service import PurgeService, get_purge_service
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/v1", dependencies=[Depends(verify_service_identity)])

HTTP_STATUS_OK = 200


@router.post("/purge", response_model=PurgeResponse, status_code=HTTP_STATUS_OK)
async def purge(
    request: PurgeRequest,
    service: Annotated[PurgeService, Depends(get_purge_service)],
) -> PurgeResponse:
    """Delete every memory row of the given playthroughs and of the given scenarios'
    templates that no remaining playthrough references. Idempotent: unknown ids count 0."""
    return await service.purge(request)


@router.get("/scopes", response_model=ScopesResponse, status_code=HTTP_STATUS_OK)
async def list_scopes(
    service: Annotated[PurgeService, Depends(get_purge_service)],
) -> ScopesResponse:
    """List every playthrough and template scope held by memory, for orphan reconciliation."""
    return await service.list_scopes()
