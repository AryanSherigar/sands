import pytest
from app.config import get_settings
from app.db.pool import close_pool, get_connection, get_pool, open_pool
from app.exceptions.db_exceptions import DatabaseUnavailableError


@pytest.fixture
async def open_dev_pool():
    pool = await open_pool()
    yield pool
    await close_pool()


def test_pool_before_open_raises() -> None:
    with pytest.raises(RuntimeError):
        get_pool()


async def test_connection_runs_a_query(open_dev_pool) -> None:
    connections = get_connection()
    connection = await anext(connections)
    cursor = await connection.execute("SELECT 1")
    assert await cursor.fetchone() == (1,)
    await connections.aclose()


async def test_pool_after_close_raises() -> None:
    await open_pool()
    await close_pool()
    with pytest.raises(RuntimeError):
        get_pool()


async def test_exhausted_pool_raises_database_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("SIMULATION_DB_POOL_MAX_SIZE", "1")
    monkeypatch.setenv("SIMULATION_DB_POOL_TIMEOUT_SECONDS", "0.2")
    get_settings.cache_clear()
    await open_pool()
    try:
        held = get_connection()
        await anext(held)
        with pytest.raises(DatabaseUnavailableError):
            await anext(get_connection())
        await held.aclose()
    finally:
        await close_pool()
