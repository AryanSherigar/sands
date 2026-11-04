"""Integration tests for expired-row cleanup."""

from datetime import UTC, datetime, timedelta

from app.db.models.rate_limit import RateLimitCounter
from app.services.rate_limit.cleanup_service import run_cleanup_once
from app.services.rate_limit.store import PostgresRateLimitStore
from sqlalchemy.ext.asyncio import AsyncSession


async def test_cleanup_deletes_only_expired_rows(
    rate_limit_store: PostgresRateLimitStore, test_engine
) -> None:
    now = datetime.now(UTC)
    async with AsyncSession(test_engine) as session:
        session.add_all(
            [
                RateLimitCounter(
                    key="old",
                    window_start=now - timedelta(days=3),
                    count=1,
                    expires_at=now - timedelta(days=1),
                ),
                RateLimitCounter(
                    key="new",
                    window_start=now,
                    count=1,
                    expires_at=now + timedelta(days=1),
                ),
            ]
        )
        await session.commit()

    assert await run_cleanup_once(rate_limit_store) == 1
