"""Shared pytest fixtures for Turn Resolution Service tests."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from app.config import settings
from app.db.base import Base
from app.db.models.rate_limit import RateLimitCounter, RateLimitStreamLease
from app.services.rate_limit.exemption_service import (
    ExemptionService,
    clear_exemption_cache,
    get_exemption_service,
)
from app.services.rate_limit.store import PostgresRateLimitStore, get_rate_limit_store
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

settings.environment = "testing"
# NOTE: Suites that exercise limits opt back in via the rate_limit_enabled
# fixture; everything else runs unthrottled.
settings.is_rate_limit_enabled = False

TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/sands_test_db"
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create TRS's mirrored schema in an isolated test database for the session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Provide a session bound to the test engine, isolated per test."""
    async_session = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client for router-level integration tests, bound to the test DB session."""
    from app.db.connection import get_db_session, get_db_session_factory
    from app.main import app as fastapi_app

    async def override_get_db_session():
        yield db_session

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    fastapi_app.dependency_overrides[get_db_session_factory] = lambda: (
        async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    )
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://testserver"
    ) as client:
        yield client
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def rate_limit_store(test_engine) -> AsyncGenerator[PostgresRateLimitStore, None]:
    # NOTE: A real, independent session factory -- the store must commit its
    # own short transactions, exactly as in production, never ride on the
    # test's db_session.
    factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    yield PostgresRateLimitStore(factory)
    async with factory() as session:
        await session.execute(delete(RateLimitCounter))
        await session.execute(delete(RateLimitStreamLease))
        await session.commit()


@pytest_asyncio.fixture
async def rate_limit_enabled(
    rate_limit_store, test_engine, monkeypatch
) -> AsyncGenerator[PostgresRateLimitStore, None]:
    from app.main import app as fastapi_app

    monkeypatch.setattr(settings, "is_rate_limit_enabled", True)
    clear_exemption_cache()
    factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    fastapi_app.dependency_overrides[get_rate_limit_store] = lambda: rate_limit_store
    fastapi_app.dependency_overrides[get_exemption_service] = lambda: ExemptionService(
        factory
    )
    yield rate_limit_store
    fastapi_app.dependency_overrides.pop(get_rate_limit_store, None)
    fastapi_app.dependency_overrides.pop(get_exemption_service, None)
    clear_exemption_cache()
