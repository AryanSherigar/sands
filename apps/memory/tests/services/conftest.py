"""Fixtures for the retrieval service tests: a real pool over the migrated test
database and a committed world with an active embedding model."""

from collections.abc import AsyncIterator, Iterator

import pytest
import structlog
from app.services import retrieval_branches, retrieval_response, retrieval_vector
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from structlog.testing import capture_logs
from tests.repositories import helpers_retrieval as helpers
from tests.services.retrieval_service_helpers import activate_model

RETRIEVAL_POOL_MAX_SIZE = 6


@pytest.fixture
async def retrieval_pool(
    migrated_test_database_url: str, db_connection: AsyncConnection
) -> AsyncIterator[AsyncConnectionPool]:
    """Depends on db_connection so the tables are emptied before the pool is used."""
    connection_pool = AsyncConnectionPool(
        migrated_test_database_url,
        min_size=1,
        max_size=RETRIEVAL_POOL_MAX_SIZE,
        open=False,
    )
    await connection_pool.open()
    yield connection_pool
    await connection_pool.close()


@pytest.fixture
async def retrieval_world(db_connection: AsyncConnection) -> helpers.World:
    world = await helpers.build_world(db_connection)
    await activate_model(db_connection)
    await db_connection.commit()
    return world


@pytest.fixture
def captured_logs(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, object]]]:
    """Structured log events emitted by every retrieval module."""
    with capture_logs() as entries:
        for module in (
            retrieval_branches,
            retrieval_response,
            retrieval_vector,
        ):
            monkeypatch.setattr(module, "logger", structlog.get_logger())
        yield entries
