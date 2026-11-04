from typing import Annotated
from uuid import UUID

from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from app.services.rate_limit.stream_lease_service import (
    StreamLeaseService,
    get_stream_lease_service,
    stream_subject_for_user,
)
from app.services.strategy_epilogue_service import build_epilogue_response
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

router = APIRouter(
    prefix="/v1/strategy/playthroughs",
    tags=["strategy-epilogue"],
)


class EpilogueStreamInput(BaseModel):
    client_request_id: UUID


@router.post("/{playthrough_id}/epilogue/stream", response_model=None)
async def stream_epilogue_entry(
    playthrough_id: UUID,
    request: EpilogueStreamInput,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
    leases: Annotated[StreamLeaseService, Depends(get_stream_lease_service)],
    authorization: Annotated[str | None, Header()] = None,
    dev_user_id: Annotated[str | None, Header(alias="X-Dev-User-Id")] = None,
) -> EventSourceResponse:
    """Stream the chronicler's closing entry for an ended playthrough, saved once."""
    return await leases.guard(
        stream_subject_for_user(user.user_id),
        lambda: build_epilogue_response(
            playthrough_id,
            request.client_request_id,
            authorization,
            dev_user_id,
            user.user_id,
            quota,
        ),
    )
