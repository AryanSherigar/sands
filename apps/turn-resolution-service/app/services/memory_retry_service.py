"""Player-facing "Retry memory": membership check, relay pass, memory retry."""

import uuid

import structlog
from app.exceptions.turn_exceptions import (
    ParticipantAccessDeniedError,
    PlaythroughNotActiveError,
)
from app.integrations import memory_client
from app.models.memory_retry import MemoryRetryResponse
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.services import memory_relay_service
from app.turn.steps.memory_degraded import REASON_DELIVERY_LAG, has_delivery_lag
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

EVENT_MEMORY_RETRY_REQUESTED = "memory_retry_requested"


async def _require_membership(
    session: AsyncSession, playthrough_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    participants = await ParticipantRepo(session).list_by_playthrough(playthrough_id)
    if not any(participant.user_id == user_id for participant in participants):
        raise ParticipantAccessDeniedError()


async def retry_memory(
    session: AsyncSession, playthrough_id: uuid.UUID, user_id: uuid.UUID
) -> MemoryRetryResponse:
    """Never replays a turn. Playthroughs that never registered with memory have
    nothing to retry and report no reasons."""
    await _require_membership(session, playthrough_id, user_id)
    playthrough = await PlaythroughRepo(session).get_by_id(playthrough_id)
    if playthrough is None:
        raise PlaythroughNotActiveError()
    if playthrough.memory_publish_revision is None:
        return MemoryRetryResponse()
    await memory_relay_service.deliver_best_effort(playthrough_id)
    result = await memory_client.retry_memory(playthrough_id)
    reasons = list(result.degraded_reasons)
    is_lagging = await has_delivery_lag(
        MemoryOutboxRepo(session), playthrough_id, playthrough.turn_count
    )
    if is_lagging:
        reasons.append(REASON_DELIVERY_LAG)
    logger.info(
        EVENT_MEMORY_RETRY_REQUESTED,
        playthrough_id=str(playthrough_id),
        batches_reset=result.batches_reset,
        degraded_reasons=reasons,
    )
    return MemoryRetryResponse(degraded_reasons=reasons)
