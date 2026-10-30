"""Retrieves recall from the memory service for a turn.

Failures here are caught, logged and degraded to an empty memory context with
reason `retrieval_failed` (ADR-5: memory must never block gameplay). The
narrator prompt then falls back to its bounded inline lore.
"""

import asyncio
import time
import uuid

import structlog
from app.config import settings
from app.exceptions.memory_exceptions import MemoryRetrieveError
from app.integrations import memory_client
from app.models.memory import (
    REASON_MEMORY_DISABLED,
    REASON_RETRIEVAL_FAILED,
    MemoryContext,
    RetrieveRequest,
    RetrieveResponse,
)
from app.models.turn import LoadedState, RecentTurn, TurnRequest
from app.services import memory_relay_service
from app.turn.retrieval_inputs import build_retrieve_request

logger = structlog.get_logger()

EVENT_TURN_STEP_COMPLETED = "turn_step_completed"
EVENT_CONTEXT_RETRIEVAL_DEGRADED = "context_retrieval_degraded"
STEP_NAME = "context_retrieval"


async def retrieve_context(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    recent_turns: list[RecentTurn],
    participant_names: dict[uuid.UUID, str],
) -> MemoryContext:
    """Query memory for what is relevant to this turn's action."""
    start_time = time.monotonic()
    if not settings.memory_retrieval_enabled:
        return MemoryContext(reasons=[REASON_MEMORY_DISABLED])
    if loaded_state.memory_publish_revision is None:
        return _failed_context(turn_request, "legacy_unregistered")
    request = build_retrieve_request(
        turn_request, loaded_state, recent_turns, participant_names
    )
    response = await _retrieve_safe(request)
    return _context_from(response, (time.monotonic() - start_time) * 1000)


def _context_from(
    response: RetrieveResponse | None, duration_ms: float
) -> MemoryContext:
    retrieval_ms = round(duration_ms)
    if response is None:
        return MemoryContext(
            reasons=[REASON_RETRIEVAL_FAILED], retrieval_ms=retrieval_ms
        )
    logger.info(
        EVENT_TURN_STEP_COMPLETED,
        step_name=STEP_NAME,
        items_returned=len(response.items),
        degraded_reasons=response.degraded_reasons,
        skipped_branches=response.skipped_branches,
        duration_ms=duration_ms,
    )
    return MemoryContext(
        response=response,
        reasons=list(response.degraded_reasons),
        retrieval_ms=retrieval_ms,
    )


def _failed_context(turn_request: TurnRequest, reason: str) -> MemoryContext:
    logger.info(
        EVENT_CONTEXT_RETRIEVAL_DEGRADED,
        playthrough_id=str(turn_request.playthrough_id),
        error_type=reason,
    )
    return MemoryContext(reasons=[REASON_RETRIEVAL_FAILED])


async def _retrieve_safe(request: RetrieveRequest) -> RetrieveResponse | None:
    # NOTE: Intentionally broad after the typed handler. Memory is optional for
    # a turn; nothing it does may fail one.
    try:
        return await _retrieve_with_registration_retry(request)
    except MemoryRetrieveError as exc:
        _log_degraded(request.playthrough_id, type(exc).__name__, exc.code)
    except Exception as exc:  # noqa: BLE001 - logged, turn proceeds without memory
        _log_degraded(request.playthrough_id, type(exc).__name__, None)
    return None


async def _retrieve_with_registration_retry(
    request: RetrieveRequest,
) -> RetrieveResponse:
    """A first turn can beat the sweep, so memory may not know the playthrough
    yet. Deliver the pending registration once, wait a moment for memory to
    apply it, then ask again once."""
    try:
        return await memory_client.retrieve(request)
    except MemoryRetrieveError as exc:
        if not exc.is_not_registered:
            raise
    await memory_relay_service.deliver_best_effort(request.playthrough_id)
    await asyncio.sleep(settings.memory_registration_retry_delay_seconds)
    return await memory_client.retrieve(request)


def _log_degraded(
    playthrough_id: uuid.UUID, error_type: str, error_code: str | None
) -> None:
    logger.warning(
        EVENT_CONTEXT_RETRIEVAL_DEGRADED,
        playthrough_id=str(playthrough_id),
        error_type=error_type,
        error_code=error_code,
    )
