import asyncio

import pytest
from alembic import command
from alembic.config import Config
from app.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

SCRATCH_DATABASE = "sands_migration_check"
ADMIN_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
SCRATCH_URL = (
    f"postgresql+asyncpg://postgres:postgres@localhost:5432/{SCRATCH_DATABASE}"
)


async def _recreate_scratch_database() -> None:
    engine = create_async_engine(
        ADMIN_URL, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with engine.connect() as connection:
        await connection.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DATABASE}"))
        await connection.execute(text(f"CREATE DATABASE {SCRATCH_DATABASE}"))
    await engine.dispose()


async def _drop_scratch_database() -> None:
    engine = create_async_engine(
        ADMIN_URL, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with engine.connect() as connection:
        await connection.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DATABASE}"))
    await engine.dispose()


@pytest.fixture
async def migrated_scratch_database(monkeypatch):
    await _recreate_scratch_database()
    monkeypatch.setattr(settings, "database_url", SCRATCH_URL)
    config = Config("alembic.ini")
    await asyncio.to_thread(command.upgrade, config, "head")
    yield config
    await _drop_scratch_database()
