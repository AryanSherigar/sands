"""Counter store behind every burst limit, quota and stream lease.

RateLimitStore is the swap point for a future Redis implementation (ADR-13).
The Postgres store opens its own short session per operation and commits it
immediately, so a reservation never rides on (or is rolled back with) the
request's own transaction.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.db.connection import AsyncSessionFactory
from app.repositories.rate_limit_repo import RateLimitRepo, WindowHit
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

SessionFactory = Callable[[], AsyncSession]

STORE_ERRORS = (SQLAlchemyError, OSError)
EVENT_RATE_LIMIT_STORE_ERROR = "rate_limit_store_error"


@dataclass(frozen=True)
class CounterLimit:
    key: str
    limit: int


@dataclass(frozen=True)
class ReserveResult:
    window_start: datetime | None
    exceeded_key: str | None

    @property
    def is_reserved(self) -> bool:
        return self.exceeded_key is None


class RateLimitStore(Protocol):
    async def hit_sliding_window(self, key: str, window_seconds: int) -> WindowHit: ...

    async def reserve(
        self, limits: Sequence[CounterLimit], window_seconds: int
    ) -> ReserveResult: ...

    async def refund(self, keys: Sequence[str], window_start: datetime) -> None: ...

    async def current_count(self, key: str, window_seconds: int) -> int: ...

    async def delete_expired(self, lock_id: int) -> int | None: ...


class PostgresRateLimitStore:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def hit_sliding_window(self, key: str, window_seconds: int) -> WindowHit:
        async with self._session_factory() as session:
            hit = await RateLimitRepo(session).hit_window(key, window_seconds)
            await session.commit()
            return hit

    async def reserve(
        self, limits: Sequence[CounterLimit], window_seconds: int
    ) -> ReserveResult:
        """Take one unit from every counter, or from none of them."""
        async with self._session_factory() as session:
            repo = RateLimitRepo(session)
            window_start: datetime | None = None
            for counter in limits:
                window_start = await repo.reserve(
                    counter.key, window_seconds, counter.limit
                )
                if window_start is None:
                    await session.rollback()
                    return ReserveResult(window_start=None, exceeded_key=counter.key)
            await session.commit()
            return ReserveResult(window_start=window_start, exceeded_key=None)

    async def refund(self, keys: Sequence[str], window_start: datetime) -> None:
        async with self._session_factory() as session:
            repo = RateLimitRepo(session)
            for key in keys:
                await repo.refund(key, window_start)
            await session.commit()

    async def current_count(self, key: str, window_seconds: int) -> int:
        async with self._session_factory() as session:
            return await RateLimitRepo(session).current_count(key, window_seconds)

    async def delete_expired(self, lock_id: int) -> int | None:
        """Delete expired rows; None when another instance holds the cleanup lock."""
        async with self._session_factory() as session:
            repo = RateLimitRepo(session)
            if not await repo.try_cleanup_lock(lock_id):
                return None
            deleted = await repo.delete_expired()
            await session.commit()
            return deleted


def get_rate_limit_store() -> RateLimitStore:
    """FastAPI dependency; overridden in tests to bind the test engine."""
    return PostgresRateLimitStore(AsyncSessionFactory)
