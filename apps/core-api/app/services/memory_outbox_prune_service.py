"""Deletes delivered memory outbox rows past their retention window."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from app.config import settings
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

EVENT_OUTBOX_PRUNED = "memory_outbox_pruned"


@dataclass(frozen=True)
class PruneResult:
    row_count: int
    is_dry_run: bool


async def prune_delivered_outbox(
    session: AsyncSession, is_dry_run: bool, now: datetime | None = None
) -> PruneResult:
    """Each batch commits on its own so a long prune never holds one big transaction."""
    cutoff = (now or datetime.now(UTC)) - timedelta(
        days=settings.memory_outbox_retention_days
    )
    repo = MemoryOutboxRepo(session)
    if is_dry_run:
        return PruneResult(await repo.count_delivered_before(cutoff), True)
    total = 0
    while True:
        deleted = await repo.delete_delivered_before(
            cutoff, settings.account_purge_batch_size
        )
        await session.commit()
        total += deleted
        if deleted < settings.account_purge_batch_size:
            break
    logger.info(EVENT_OUTBOX_PRUNED, row_count=total)
    return PruneResult(total, False)
