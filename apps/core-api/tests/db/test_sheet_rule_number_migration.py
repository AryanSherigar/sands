"""Two sheet rules may share a number; the key stays unique."""

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

TABLE = "scenario_sheet_rules"
NUMBER_CONSTRAINT = "uq_scenario_sheet_rules_number"
KEY_CONSTRAINT = "uq_scenario_sheet_rules_key"
PREVIOUS_REVISION = "031_refresh_rotation_grace"


def _only_sheet_rules(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name == TABLE
    return getattr(getattr(obj, "table", None), "name", None) == TABLE


async def _constraints_and_differences():
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.connect() as connection:

        def read(sync_connection):
            names = {
                item["name"]
                for item in inspect(sync_connection).get_unique_constraints(TABLE)
            }
            context = MigrationContext.configure(
                sync_connection,
                opts={"compare_type": True, "include_object": _only_sheet_rules},
            )
            return names, compare_metadata(context, Base.metadata)

        result = await connection.run_sync(read)
    await engine.dispose()
    return result


async def test_the_number_is_no_longer_unique_and_matches_the_orm(
    migrated_scratch_database,
):
    names, differences = await _constraints_and_differences()
    assert NUMBER_CONSTRAINT not in names
    assert KEY_CONSTRAINT in names
    assert differences == []


async def test_downgrade_restores_the_number_constraint(migrated_scratch_database):
    await asyncio.to_thread(
        command.downgrade, migrated_scratch_database, PREVIOUS_REVISION
    )
    names, _ = await _constraints_and_differences()
    assert NUMBER_CONSTRAINT in names
