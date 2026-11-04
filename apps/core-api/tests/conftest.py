import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from app.config import settings
from app.db.base import Base
from app.db.connection import get_db_session, get_session_factory
from app.db.models.rate_limit import RateLimitCounter, RateLimitStreamLease
from app.db.models.scenario import Scenario
from app.main import app as fastapi_app
from app.models.memory_purge import MemoryPurgeResult
from app.services.rate_limit.exemption_service import clear_exemption_cache
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
def event_loop():
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def scenario_memory_purge():
    """Hard-deleting a scenario calls memory; keep tests off the network.

    Patches the shared memory_client module, so only suites that delete scenarios
    opt in; the client's own tests must see the real function."""
    with patch(
        "app.services.scenario_service.memory_client.purge",
        new_callable=AsyncMock,
        return_value=MemoryPurgeResult(),
    ) as purge:
        yield purge


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db_session():
        yield db_session

    @asynccontextmanager
    async def _shared_session_cm() -> AsyncGenerator[AsyncSession, None]:
        # Reuses the same test session/connection rather than opening a new
        # one, so a background publish job can see writes the test made
        # earlier in the same (uncommitted) test transaction.
        yield db_session

    def override_get_session_factory():
        return _shared_session_cm

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    fastapi_app.dependency_overrides[get_session_factory] = override_get_session_factory
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://testserver"
    ) as client:
        yield client
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client_real_background(
    db_session, test_engine
) -> AsyncGenerator[AsyncClient, None]:
    # NOTE: Unlike async_client's override, this commits db_session after
    # every request, mirroring production get_db_session's scope="function"
    # commit-after-yield contract. Without it, a request's writes (e.g. a
    # newly created job row) never become visible to the independent
    # background session below, which would otherwise see nothing and
    # silently no-op -- not the concurrency bug this fixture exists to catch.
    async def override_get_db_session():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    # NOTE: Binds get_session_factory to a real async_sessionmaker on
    # test_engine, so a background job opens its own independent
    # connection/transaction against the test DB -- the same shape as
    # production's AsyncSessionFactory. Use this for tests that need to catch
    # bugs from the request and background sessions genuinely being separate
    # (see ADR-010's publish deadlock).
    real_session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    def override_get_session_factory():
        return real_session_factory

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    fastapi_app.dependency_overrides[get_session_factory] = override_get_session_factory
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://testserver"
    ) as client:
        yield client
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def cleanup_scenarios(db_session) -> AsyncGenerator[list[uuid.UUID], None]:
    scenario_ids: list[uuid.UUID] = []
    yield scenario_ids
    if scenario_ids:
        await db_session.execute(
            delete(Scenario).where(Scenario.scenario_id.in_(scenario_ids))
        )
        await db_session.commit()


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
    rate_limit_store, monkeypatch
) -> AsyncGenerator[PostgresRateLimitStore, None]:
    monkeypatch.setattr(settings, "is_rate_limit_enabled", True)
    clear_exemption_cache()
    fastapi_app.dependency_overrides[get_rate_limit_store] = lambda: rate_limit_store
    yield rate_limit_store
    fastapi_app.dependency_overrides.pop(get_rate_limit_store, None)
    clear_exemption_cache()
