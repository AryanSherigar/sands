"""FastAPI router for multiplayer notifications and spectator streaming."""

import asyncio
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Annotated

import structlog
from app.config import settings
from app.db.connection import get_db_session
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.routers.alpha_guards import forbid_in_alpha_mode
from app.services.rate_limit.client_identity import resolve_client_ip
from app.services.rate_limit.stream_lease_service import (
    StreamLeaseService,
    get_stream_lease_service,
    stream_subject_for_ip,
    stream_subject_for_user,
)
from app.session import access, notification_manager, spectator_manager
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

router = APIRouter(
    prefix="/v1/session",
    tags=["Session"],
    dependencies=[Depends(forbid_in_alpha_mode)],
)
logger = structlog.get_logger()

EVENT_SPECTATE_STREAM_OPENED = "spectate_stream_opened"
EVENT_NOTIFICATION_STREAM_OPENED = "notification_stream_opened"


@router.get("/{playthrough_id}/spectate", response_model=None)
async def spectate(
    request: Request,
    playthrough_id: uuid.UUID,
    share_token: Annotated[str, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    stream_leases: Annotated[StreamLeaseService, Depends(get_stream_lease_service)],
) -> EventSourceResponse:
    """Read-only live narration stream, gated on a valid spectate share token."""
    await access.validate_spectate_access(playthrough_id, share_token, session)

    async def build_response() -> EventSourceResponse:
        logger.info(EVENT_SPECTATE_STREAM_OPENED, playthrough_id=str(playthrough_id))
        queue = spectator_manager.subscribe(playthrough_id)
        return EventSourceResponse(
            _relay(queue, lambda: spectator_manager.unsubscribe(playthrough_id, queue)),
            ping=settings.sse_ping_interval_seconds,
        )

    subject = stream_subject_for_ip(resolve_client_ip(request))
    return await stream_leases.guard(subject, build_response)


@router.get("/{playthrough_id}/notifications", response_model=None)
async def notifications(
    playthrough_id: uuid.UUID,
    participant_id: Annotated[uuid.UUID, Query()],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    stream_leases: Annotated[StreamLeaseService, Depends(get_stream_lease_service)],
) -> EventSourceResponse:
    """Persistent SSE channel for 'your_turn' notifications in multiplayer play."""
    await access.validate_notification_access(
        playthrough_id, participant_id, user.user_id, session
    )

    async def build_response() -> EventSourceResponse:
        logger.info(
            EVENT_NOTIFICATION_STREAM_OPENED, playthrough_id=str(playthrough_id)
        )
        queue = notification_manager.subscribe(playthrough_id, participant_id)
        return EventSourceResponse(
            _relay(
                queue,
                lambda: notification_manager.unsubscribe(
                    playthrough_id, participant_id, queue
                ),
            ),
            ping=settings.sse_ping_interval_seconds,
        )

    return await stream_leases.guard(
        stream_subject_for_user(user.user_id), build_response
    )


async def _relay(
    queue: asyncio.Queue[tuple[str, str]], on_disconnect: Callable[[], None]
) -> AsyncIterator[ServerSentEvent]:
    """Drain a subscriber queue as SSE events, unsubscribing on disconnect."""
    try:
        while True:
            event_name, data = await queue.get()
            yield ServerSentEvent(event=event_name, data=data)
    finally:
        on_disconnect()
