"""POST /v1/retrieve. Service-authenticated."""

from typing import Annotated

from app.middleware.service_auth import verify_service_identity
from app.models.retrieve import RetrieveRequest, RetrieveResponse
from app.services.retrieval_service import RetrievalService, get_retrieval_service
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/v1/retrieve", dependencies=[Depends(verify_service_identity)]
)

HTTP_STATUS_OK = 200


@router.post("", response_model=RetrieveResponse, status_code=HTTP_STATUS_OK)
async def retrieve(
    request: RetrieveRequest,
    service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> RetrieveResponse:
    """Eligibility-first hybrid recall for one turn.

    Never raises for an embedding or BM25 failure; the skipped branch is listed in
    `skipped_branches`. Returns 409 `not_registered` for an unknown playthrough and
    422 when a request input limit is exceeded."""
    return await service.retrieve(request)
