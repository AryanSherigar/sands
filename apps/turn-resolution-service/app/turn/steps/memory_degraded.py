"""Builds the memory_degraded SSE event shown as a non-blocking notice.

Reasons are memory's own (carried by retrieval), `retrieval_failed`, and TRS's
`delivery_lag`: outbox rows still undelivered after the recent window has moved
past them. Playthroughs that never registered with memory report nothing.
"""

import uuid

from app.config import settings
from app.models.memory import REASON_MEMORY_DISABLED
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.turn.steps import response_streamer
from sse_starlette.sse import ServerSentEvent

REASON_DELIVERY_LAG = "delivery_lag"


async def has_delivery_lag(
    outbox_repo: MemoryOutboxRepo, playthrough_id: uuid.UUID, turn_number: int
) -> bool:
    oldest_lagging_sequence = turn_number - settings.recent_window_turns
    if oldest_lagging_sequence < 1:
        return False
    return await outbox_repo.has_undelivered_through(
        playthrough_id, oldest_lagging_sequence
    )


async def build_memory_degraded_event(
    outbox_repo: MemoryOutboxRepo | None,
    playthrough_id: uuid.UUID,
    turn_number: int,
    retrieval_reasons: list[str],
) -> ServerSentEvent | None:
    if outbox_repo is None:
        return None
    reasons = [
        reason for reason in retrieval_reasons if reason != REASON_MEMORY_DISABLED
    ]
    if await has_delivery_lag(outbox_repo, playthrough_id, turn_number):
        reasons.append(REASON_DELIVERY_LAG)
    if not reasons:
        return None
    return response_streamer.memory_degraded_event(reasons)
