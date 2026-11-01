from typing import Annotated
from uuid import UUID

from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.routers.alpha_guards import forbid_when_turns_suspended
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from app.services.rate_limit.stream_lease_service import (
    StreamLeaseService,
    get_stream_lease_service,
    stream_subject_for_user,
)
from app.services.strategy_dispatch_service import build_dispatch_response
from fastapi import APIRouter, Depends, Header, Path
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from strategy_contracts.agents import MAX_RUMOR_ID_CHARS, RUMOR_ID_PATTERN

router = APIRouter(
    prefix="/v1/strategy/playthroughs",
    tags=["strategy-dispatches"],
    dependencies=[Depends(forbid_when_turns_suspended)],
)
RumorId = Annotated[
    str, Path(min_length=1, max_length=MAX_RUMOR_ID_CHARS, pattern=RUMOR_ID_PATTERN)
]


class DispatchStreamInput(BaseModel):
    client_request_id: UUID


@router.post("/{playthrough_id}/dispatches/{rumor_id}/stream", response_model=None)
async def stream_dispatch_letter(
    playthrough_id: UUID,
    rumor_id: RumorId,
    request: DispatchStreamInput,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
    leases: Annotated[StreamLeaseService, Depends(get_stream_lease_service)],
    authorization: Annotated[str | None, Header()] = None,
    dev_user_id: Annotated[str | None, Header(alias="X-Dev-User-Id")] = None,
) -> EventSourceResponse:
    """Stream an owned spymaster dispatch without running a gameplay turn."""
    return await leases.guard(
        stream_subject_for_user(user.user_id),
        lambda: build_dispatch_response(
            playthrough_id,
            rumor_id,
            request.client_request_id,
            authorization,
            dev_user_id,
            user.user_id,
            quota,
        ),
    )
