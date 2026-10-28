"""AsyncConnectionPool lifecycle and FastAPI dependency for Postgres access."""

from collections.abc import AsyncGenerator

from app.config import get_settings
from app.exceptions.db_exceptions import DatabaseUnavailableError
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool, PoolTimeout

_pool: AsyncConnectionPool | None = None


async def open_pool() -> AsyncConnectionPool:
    """Create and open the process-wide pool. Call once from the FastAPI lifespan startup."""
    global _pool
    settings = get_settings()
    _pool = AsyncConnectionPool(
        conninfo=settings.simulation_database_url,
        min_size=settings.simulation_db_pool_min_size,
        max_size=settings.simulation_db_pool_max_size,
        timeout=settings.simulation_db_pool_timeout_seconds,
        open=False,
    )
    await _pool.open()
    return _pool


async def close_pool() -> None:
    """Close the process-wide pool. Call once from the FastAPI lifespan shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError(
            "Connection pool is not open; call open_pool() from lifespan startup first."
        )
    return _pool


async def get_connection() -> AsyncGenerator[AsyncConnection, None]:
    """FastAPI dependency yielding a pooled connection.

    Usage in a service's dependency provider:
        async def get_thing_service(
            connection: Annotated[AsyncConnection, Depends(get_connection)],
        ) -> ThingService:
            return ThingService(ThingRepo(connection))
    """
    pool = get_pool()
    try:
        async with pool.connection() as connection:
            yield connection
    except PoolTimeout as error:
        raise DatabaseUnavailableError() from error
