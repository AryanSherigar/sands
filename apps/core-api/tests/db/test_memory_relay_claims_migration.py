"""The claim migration matches both ORM shape and downgrade boundaries."""

import asyncio

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db.base import Base
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from tests.db.migration_test_helpers import (
    SCRATCH_URL,
)
from tests.db.migration_test_helpers import (
    migrated_scratch_database as migrated_scratch_database,
)

CLAIM_TABLE = "memory_relay_claims"
PREVIOUS_REVISION = "029_add_alpha_user_suspension"


def _include_claim(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name == CLAIM_TABLE
    return getattr(getattr(obj, "table", None), "name", None) == CLAIM_TABLE


async def _schema():
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.connect() as connection:

        def read(sync_connection):
            context = MigrationContext.configure(
                sync_connection,
                opts={
                    "compare_type": True,
                    "include_object": _include_claim,
                },
            )
            return set(inspect(sync_connection).get_table_names()), compare_metadata(
                context, Base.metadata
            )

        result = await connection.run_sync(read)
    await engine.dispose()
    return result


async def test_claim_migration_matches_orm(migrated_scratch_database):
    tables, differences = await _schema()
    assert CLAIM_TABLE in tables
    assert differences == []


async def test_claim_downgrade_keeps_existing_product_tables(migrated_scratch_database):
    await asyncio.to_thread(
        command.downgrade, migrated_scratch_database, PREVIOUS_REVISION
    )
    tables, _ = await _schema()
    assert CLAIM_TABLE not in tables
    assert {"memory_outbox", "playthroughs", "turn_logs"} <= tables
