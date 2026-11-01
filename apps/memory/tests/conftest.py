"""Shared Postgres fixtures. All DB setup is lazy: tests that request no DB fixture never connect."""

from collections.abc import AsyncIterator

import pytest
from app.config import get_settings
from app.db.migrate import apply_migrations
from pgvector.psycopg import register_vector_async
from psycopg import AsyncConnection, sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

# NOTE: "postgres" always exists, so dropping the test DB never depends on the dev DB.
MAINTENANCE_DATABASE_NAME = "postgres"
SCRATCH_DATABASE_NAME = "memory_migrate_test_db"
MEMORY_TABLE_PREFIX_PATTERN = "memory\\_%"

DROP_DATABASE = "DROP DATABASE IF EXISTS {database} WITH (FORCE)"
CREATE_DATABASE = "CREATE DATABASE {database}"
SELECT_MEMORY_TABLES = (
    "SELECT tablename FROM pg_tables "
    "WHERE schemaname = 'public' AND tablename LIKE %s ORDER BY tablename"
)
TRUNCATE_TABLES = "TRUNCATE {tables} RESTART IDENTITY CASCADE"


def _database_url_for(base_url: str, database_name: str) -> str:
    return make_conninfo(base_url, dbname=database_name)


def _database_name_of(database_url: str) -> str:
    return str(conninfo_to_dict(database_url)["dbname"])


async def _run_maintenance_statement(base_url: str, template: str, name: str) -> None:
    maintenance_url = _database_url_for(base_url, MAINTENANCE_DATABASE_NAME)
    statement = sql.SQL(template).format(database=sql.Identifier(name))
    async with await AsyncConnection.connect(
        maintenance_url, autocommit=True
    ) as connection:
        await connection.execute(statement)


async def recreate_database(base_url: str, database_name: str) -> str:
    """Drop (forcibly) and create an empty database; return its URL."""
    await _run_maintenance_statement(base_url, DROP_DATABASE, database_name)
    await _run_maintenance_statement(base_url, CREATE_DATABASE, database_name)
    return _database_url_for(base_url, database_name)


async def drop_database(base_url: str, database_name: str) -> None:
    await _run_maintenance_statement(base_url, DROP_DATABASE, database_name)


async def _truncate_memory_tables(connection: AsyncConnection) -> None:
    cursor = await connection.execute(
        SELECT_MEMORY_TABLES, (MEMORY_TABLE_PREFIX_PATTERN,)
    )
    table_names = [row[0] for row in await cursor.fetchall()]
    tables = sql.SQL(", ").join(sql.Identifier(name) for name in table_names)
    await connection.execute(sql.SQL(TRUNCATE_TABLES).format(tables=tables))
    await connection.commit()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return get_settings().memory_test_database_url


@pytest.fixture(scope="session")
async def migrated_test_database_url(test_database_url: str) -> str:
    """memory_test_db, recreated empty and migrated once per session, on first use."""
    database_name = _database_name_of(test_database_url)
    database_url = await recreate_database(test_database_url, database_name)
    await apply_migrations(database_url)
    return database_url


@pytest.fixture
async def db_connection(
    migrated_test_database_url: str,
) -> AsyncIterator[AsyncConnection]:
    """A non-autocommit connection to a migrated memory_test_db with every memory_* table emptied.

    The test owns the transaction; uncommitted work is rolled back on close.
    pgvector types are registered, so `pgvector.Vector` values bind and load.
    """
    connection = await AsyncConnection.connect(migrated_test_database_url)
    try:
        await register_vector_async(connection)
        await _truncate_memory_tables(connection)
        yield connection
    finally:
        await connection.close()


@pytest.fixture
async def scratch_database_url(test_database_url: str) -> AsyncIterator[str]:
    """An empty, unmigrated throwaway database, dropped after the test."""
    database_url = await recreate_database(test_database_url, SCRATCH_DATABASE_NAME)
    yield database_url
    await drop_database(test_database_url, SCRATCH_DATABASE_NAME)
