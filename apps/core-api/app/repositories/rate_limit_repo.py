"""Rate-limit counters.

Every statement takes its time from the database's now(), so instances with
skewed clocks agree on which window a request falls in. Windows are aligned
to the Unix epoch, which makes a 86400s window exactly one UTC day.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_WINDOW_START_SQL = (
    "date_bin(make_interval(secs => CAST(:window AS integer)), now(), "
    "TIMESTAMPTZ '1970-01-01 00:00:00+00')"
)

_HIT_WINDOW_SQL = text(
    f"""
    WITH clock AS (
        SELECT now() AS ts, {_WINDOW_START_SQL} AS window_start
    ), upserted AS (
        INSERT INTO rate_limit_counters (key, window_start, count, expires_at)
        SELECT :key, clock.window_start, 1,
               clock.window_start + make_interval(secs => CAST(:window AS integer) * 2)
        FROM clock
        ON CONFLICT (key, window_start)
        DO UPDATE SET count = rate_limit_counters.count + 1
        RETURNING count
    )
    SELECT
        (SELECT count FROM upserted) AS current_count,
        COALESCE((
            SELECT previous.count FROM rate_limit_counters AS previous
            WHERE previous.key = :key
              AND previous.window_start = clock.window_start
                  - make_interval(secs => CAST(:window AS integer))
        ), 0) AS previous_count,
        EXTRACT(EPOCH FROM clock.ts - clock.window_start) AS elapsed_seconds
    FROM clock
    """
)

_RESERVE_SQL = text(
    f"""
    WITH clock AS (SELECT {_WINDOW_START_SQL} AS window_start)
    INSERT INTO rate_limit_counters (key, window_start, count, expires_at)
    SELECT :key, clock.window_start, 1,
           clock.window_start + make_interval(secs => CAST(:window AS integer) * 2)
    FROM clock
    WHERE CAST(:limit AS integer) > 0
    ON CONFLICT (key, window_start)
    DO UPDATE SET count = rate_limit_counters.count + 1
    WHERE rate_limit_counters.count < CAST(:limit AS integer)
    RETURNING window_start
    """
)

_REFUND_SQL = text(
    """
    UPDATE rate_limit_counters SET count = count - 1
    WHERE key = :key AND window_start = :window_start AND count > 0
    """
)

_CURRENT_COUNT_SQL = text(
    f"""
    SELECT COALESCE((
        SELECT count FROM rate_limit_counters
        WHERE key = :key AND window_start = {_WINDOW_START_SQL}
    ), 0)
    """
)

_DELETE_EXPIRED_COUNTERS_SQL = text(
    "DELETE FROM rate_limit_counters WHERE expires_at <= now()"
)
_DELETE_EXPIRED_LEASES_SQL = text(
    "DELETE FROM rate_limit_stream_leases WHERE expires_at <= now()"
)
_TRY_CLEANUP_LOCK_SQL = text("SELECT pg_try_advisory_xact_lock(:lock_id)")


@dataclass(frozen=True)
class WindowHit:
    current_count: int
    previous_count: int
    elapsed_seconds: float


class RateLimitRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def hit_window(self, key: str, window_seconds: int) -> WindowHit:
        result = await self.session.execute(
            _HIT_WINDOW_SQL, {"key": key, "window": window_seconds}
        )
        row = result.one()
        return WindowHit(
            current_count=row.current_count,
            previous_count=row.previous_count,
            elapsed_seconds=float(row.elapsed_seconds),
        )

    async def reserve(
        self, key: str, window_seconds: int, limit: int
    ) -> datetime | None:
        """Atomically take one unit if the window is under its limit.

        Returns the reserved window's start, or None when the limit is reached.
        """
        result = await self.session.execute(
            _RESERVE_SQL, {"key": key, "window": window_seconds, "limit": limit}
        )
        return result.scalar_one_or_none()

    async def refund(self, key: str, window_start: datetime) -> None:
        await self.session.execute(
            _REFUND_SQL, {"key": key, "window_start": window_start}
        )

    async def current_count(self, key: str, window_seconds: int) -> int:
        result = await self.session.execute(
            _CURRENT_COUNT_SQL, {"key": key, "window": window_seconds}
        )
        return result.scalar_one()

    async def try_cleanup_lock(self, lock_id: int) -> bool:
        result = await self.session.execute(_TRY_CLEANUP_LOCK_SQL, {"lock_id": lock_id})
        return bool(result.scalar_one())

    async def delete_expired(self) -> int:
        counters = await self.session.execute(_DELETE_EXPIRED_COUNTERS_SQL)
        leases = await self.session.execute(_DELETE_EXPIRED_LEASES_SQL)
        return (counters.rowcount or 0) + (leases.rowcount or 0)
