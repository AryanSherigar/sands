"""Advanced mode: nullable UI metadata on end conditions and rule invariants."""

import asyncio

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db.base import Base
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from tests.db.migration_test_helpers import (
    SCRATCH_URL,
)
from tests.db.migration_test_helpers import (
    migrated_scratch_database as migrated_scratch_database,
)

PREVIOUS_REVISION = "034_guided_creation"
CURRENT_REVISION = "035_advanced_ui_metadata"
TABLES = ("end_conditions", "rule_invariants")
METADATA_COLUMN = "metadata"
CREATOR_ID = "00000000-0000-0000-0000-0000000000a1"
SCENARIO_ID = "00000000-0000-0000-0000-0000000000b1"
SEED_STATEMENTS = (
    "INSERT INTO users (user_id, display_name, auth_provider_id) "
    f"VALUES ('{CREATOR_ID}', 'Creator', 'auth-advanced-metadata')",
    "INSERT INTO scenarios (scenario_id, creator_id, title, complexity_tier, "
    "player_count_support, mode) "
    f"VALUES ('{SCENARIO_ID}', '{CREATOR_ID}', 'S', 'newbie', 'solo', 'master')",
    "INSERT INTO end_conditions (scenario_id, outcome_tag, outcome_title, "
    f"outcome_text, priority) VALUES ('{SCENARIO_ID}', 'win', 'Out', 'Free', 2)",
    "INSERT INTO rule_invariants (scenario_id, label, applies_to, narrator_text) "
    f"VALUES ('{SCENARIO_ID}', 'Floor', 'global', 'Never below zero')",
)


def _only_touched_tables(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in TABLES
    return getattr(getattr(obj, "table", None), "name", None) in TABLES


async def _execute(*statements: str) -> None:
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.begin() as connection:
        for statement in statements:
            await connection.execute(text(statement))
    await engine.dispose()


async def _rows(statement: str) -> list[tuple]:
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.connect() as connection:
        rows = [tuple(row) for row in (await connection.execute(text(statement)))]
    await engine.dispose()
    return rows


async def _columns_and_differences():
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.connect() as connection:

        def read(sync_connection):
            inspector = inspect(sync_connection)
            columns = {
                table: {c["name"]: c for c in inspector.get_columns(table)}
                for table in TABLES
            }
            context = MigrationContext.configure(
                sync_connection,
                opts={"compare_type": True, "include_object": _only_touched_tables},
            )
            return columns, compare_metadata(context, Base.metadata)

        result = await connection.run_sync(read)
    await engine.dispose()
    return result


async def test_schema_has_nullable_metadata_columns_matching_the_orm(
    migrated_scratch_database,
):
    columns, differences = await _columns_and_differences()

    for table in TABLES:
        assert METADATA_COLUMN in columns[table]
        assert columns[table][METADATA_COLUMN]["nullable"] is True
    assert differences == []


async def test_upgrade_leaves_existing_rows_untouched_with_null_metadata(
    migrated_scratch_database,
):
    await asyncio.to_thread(
        command.downgrade, migrated_scratch_database, PREVIOUS_REVISION
    )
    await _execute(*SEED_STATEMENTS)

    await asyncio.to_thread(
        command.upgrade, migrated_scratch_database, CURRENT_REVISION
    )

    end_rows = await _rows(
        "SELECT outcome_title, outcome_text, priority, metadata FROM end_conditions"
    )
    invariant_rows = await _rows(
        "SELECT label, applies_to, narrator_text, metadata FROM rule_invariants"
    )
    assert end_rows == [("Out", "Free", 2, None)]
    assert invariant_rows == [("Floor", "global", "Never below zero", None)]


async def test_downgrade_drops_the_columns_and_keeps_the_rows(
    migrated_scratch_database,
):
    await _execute(*SEED_STATEMENTS)

    await asyncio.to_thread(
        command.downgrade, migrated_scratch_database, PREVIOUS_REVISION
    )

    columns, _ = await _columns_and_differences()
    for table in TABLES:
        assert METADATA_COLUMN not in columns[table]
    assert await _rows("SELECT outcome_title FROM end_conditions") == [("Out",)]
    assert await _rows("SELECT label FROM rule_invariants") == [("Floor",)]
