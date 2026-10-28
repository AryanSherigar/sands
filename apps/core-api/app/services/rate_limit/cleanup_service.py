"""Periodic deletion of expired rate-limit counters and stream leases.

Runs in every Core API instance; a transaction-scoped advisory lock lets only
one of them do the delete each round. TRS writes leases but never cleans up.
"""

import asyncio

import structlog
from app.config import settings
from app.services.rate_limit.store import (
    EVENT_RATE_LIMIT_STORE_ERROR,
    STORE_ERRORS,
    RateLimitStore,
)

logger = structlog.get_logger()

CLEANUP_ADVISORY_LOCK_ID = 7_310_001
EVENT_RATE_LIMIT_CLEANUP = "rate_limit_cleanup"


async def run_cleanup_once(store: RateLimitStore) -> int | None:
    try:
        deleted = await store.delete_expired(CLEANUP_ADVISORY_LOCK_ID)
    except STORE_ERRORS as error:
        logger.error(
            EVENT_RATE_LIMIT_STORE_ERROR, operation="cleanup", error=str(error)
        )
        return None
    if deleted is not None:
        logger.info(EVENT_RATE_LIMIT_CLEANUP, deleted_rows=deleted)
    return deleted


async def run_cleanup_forever(store: RateLimitStore) -> None:
    while True:
        await asyncio.sleep(settings.rate_limit_cleanup_interval_seconds)
        await run_cleanup_once(store)
