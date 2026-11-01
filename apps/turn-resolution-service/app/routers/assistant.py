"""FastAPI router for the Studio AI Assistant chat endpoint."""

from typing import Annotated

from app.config import settings
from app.middleware.auth import get_current_user
from app.models.assistant import AssistantChatRequest
from app.models.auth import CurrentUser
from app.routers.alpha_guards import forbid_in_alpha_mode
from app.services.assistant_service import open_assistant_chat
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from app.services.rate_limit.stream_lease_service import (
    StreamLeaseService,
    get_stream_lease_service,
    stream_subject_for_user,
)
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

router = APIRouter(
    prefix="/v1/studio",
    tags=["Studio Assistant"],
    dependencies=[Depends(forbid_in_alpha_mode)],
)


@router.post("/assistant", response_model=None)
async def chat_with_assistant(
    request: AssistantChatRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    quota_service: Annotated[QuotaService, Depends(get_quota_service)],
    stream_leases: Annotated[StreamLeaseService, Depends(get_stream_lease_service)],
) -> EventSourceResponse:
    """Stream studio world-building assistant guidance over SSE."""

    async def build_response() -> EventSourceResponse:
        events = await open_assistant_chat(request, user.user_id, quota_service)
        return EventSourceResponse(events, ping=settings.sse_ping_interval_seconds)

    return await stream_leases.guard(
        stream_subject_for_user(user.user_id), build_response
    )
