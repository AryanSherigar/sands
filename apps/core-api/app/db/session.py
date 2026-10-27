"""Database connection and async session management module."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

async_engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for FastAPI dependency injection."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Provide the session factory for code that needs its own DB session."""
    return AsyncSessionFactory


async def close_db_connection() -> None:
    """Dispose of the async engine's connection pool."""
    await async_engine.dispose()


__all__: list[str] = [
    "AsyncSessionFactory",
    "async_engine",
    "close_db_connection",
    "get_db_session",
    "get_session_factory",
]
