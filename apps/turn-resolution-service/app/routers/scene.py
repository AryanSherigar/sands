"""FastAPI router streaming strategy-mode scene dialogue."""

import uuid
from typing import Annotated

from app.config import settings
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.scene import SceneMessageRequest
from app.services.rate_limit.stream_lease_service import (
    StreamLeaseService,
    get_stream_lease_service,
    stream_subject_for_user,
)
from app.services.scene_service import prepare_exchange
from app.services.scene_stream_service import stream_prepared_message
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

router = APIRouter(
    prefix="/v1/scenes",
    tags=["Scenes"],
)


@router.post("/{scene_id}/messages", response_model=None)
async def send_scene_message(
    scene_id: uuid.UUID,
    request: SceneMessageRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    stream_leases: Annotated[StreamLeaseService, Depends(get_stream_lease_service)],
) -> EventSourceResponse:
    """Stream the leader's reply to one player message in an open scene."""

    async def build_response() -> EventSourceResponse:
        prepared = await prepare_exchange(scene_id, user.user_id, request)
        return EventSourceResponse(
            stream_prepared_message(prepared), ping=settings.sse_ping_interval_seconds
        )

    return await stream_leases.guard(
        stream_subject_for_user(user.user_id), build_response
    )
