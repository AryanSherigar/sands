"""Unit tests for memory_degraded.py's reason filtering."""

import uuid
from unittest.mock import AsyncMock

from app.models.memory import REASON_MEMORY_DISABLED, REASON_RETRIEVAL_FAILED
from app.turn.steps import memory_degraded


def _outbox_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.has_undelivered_through.return_value = False
    return repo


async def test_disabled_memory_is_not_shown_to_players_as_degraded() -> None:
    event = await memory_degraded.build_memory_degraded_event(
        _outbox_repo(), uuid.uuid4(), 3, [REASON_MEMORY_DISABLED]
    )

    assert event is None


async def test_real_degradation_still_produces_a_notice_alongside_disabled() -> None:
    event = await memory_degraded.build_memory_degraded_event(
        _outbox_repo(),
        uuid.uuid4(),
        3,
        [REASON_MEMORY_DISABLED, REASON_RETRIEVAL_FAILED],
    )

    assert event is not None
    assert REASON_RETRIEVAL_FAILED in str(event.data)
    assert REASON_MEMORY_DISABLED not in str(event.data)
