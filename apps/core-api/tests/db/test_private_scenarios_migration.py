"""Private scenarios: the visibility column and the allowlist table."""

import asyncio

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db.base import Base
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from tests.db.migration_test_helpers import (
    SCRATCH_URL,
)
from tests.db.migration_test_helpers import (
    migrated_scratch_database as migrated_scratch_database,
)

ACCESS_TABLE = "scenario_access"
PREVIOUS_REVISION = "032_sheet_rule_number_not_unique"
CREATOR_ID = "00000000-0000-0000-0000-0000000000a1"
SCENARIO_ID = "00000000-0000-0000-0000-0000000000b1"
INSERT_USER = (
    "INSERT INTO users (user_id, display_name, auth_provider_id) "
    f"VALUES ('{CREATOR_ID}', 'Creator', 'auth-private-migration')"
)
INSERT_SCENARIO = (
    "INSERT INTO scenarios (scenario_id, creator_id, title, complexity_tier, "
    f"player_count_support, mode) VALUES ('{SCENARIO_ID}', '{CREATOR_ID}', 'S', "
    "'master', 'solo', 'master')"
)


def _only_private_objects(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in {ACCESS_TABLE, "scenarios"}
    owner = getattr(getattr(obj, "table", None), "name", None)
    if owner == ACCESS_TABLE:
        return True
    return owner == "scenarios" and "visibility" in str(name)


async def _schema():
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.connect() as connection:

        def read(sync_connection):
            inspector = inspect(sync_connection)
            columns = {item["name"] for item in inspector.get_columns("scenarios")}
            tables = set(inspector.get_table_names())
            context = MigrationContext.configure(
                sync_connection,
                opts={"compare_type": True, "include_object": _only_private_objects},
            )
            return columns, tables, compare_metadata(context, Base.metadata)

        result = await connection.run_sync(read)
    await engine.dispose()
    return result


async def _execute(*statements: str) -> None:
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.begin() as connection:
        for statement in statements:
            await connection.execute(text(statement))
    await engine.dispose()


async def _scalar(statement: str):
    engine = create_async_engine(SCRATCH_URL, poolclass=NullPool)
    async with engine.connect() as connection:
        value = (await connection.execute(text(statement))).scalar_one()
    await engine.dispose()
    return value


async def test_the_schema_has_visibility_and_the_allowlist_and_matches_the_orm(
    migrated_scratch_database,
):
    columns, tables, differences = await _schema()
    assert "visibility" in columns
    assert ACCESS_TABLE in tables
    assert differences == []


async def test_scenarios_default_to_public(migrated_scratch_database):
    await _execute(INSERT_USER, INSERT_SCENARIO)
    value = await _scalar(
        f"SELECT visibility FROM scenarios WHERE scenario_id = '{SCENARIO_ID}'"
    )
    assert value == "public"


async def test_an_unknown_visibility_is_rejected(migrated_scratch_database):
    await _execute(INSERT_USER, INSERT_SCENARIO)
    with pytest.raises(DBAPIError):
        await _execute(
            f"UPDATE scenarios SET visibility = 'secret' WHERE scenario_id = '{SCENARIO_ID}'"
        )


async def test_allowlist_rows_go_with_their_scenario(migrated_scratch_database):
    await _execute(
        INSERT_USER,
        INSERT_SCENARIO,
        f"INSERT INTO scenario_access (scenario_id, user_id) VALUES ('{SCENARIO_ID}', '{CREATOR_ID}')",
        f"DELETE FROM scenarios WHERE scenario_id = '{SCENARIO_ID}'",
    )
    assert await _scalar("SELECT count(*) FROM scenario_access") == 0


async def test_downgrade_removes_the_feature_when_nothing_is_private(
    migrated_scratch_database,
):
    await asyncio.to_thread(
        command.downgrade, migrated_scratch_database, PREVIOUS_REVISION
    )
    columns, tables, _ = await _schema()
    assert "visibility" not in columns
    assert ACCESS_TABLE not in tables


async def test_downgrade_refuses_to_expose_a_private_scenario(
    migrated_scratch_database,
):
    await _execute(
        INSERT_USER,
        INSERT_SCENARIO,
        f"UPDATE scenarios SET visibility = 'private' WHERE scenario_id = '{SCENARIO_ID}'",
    )
    with pytest.raises(RuntimeError, match="private scenario"):
        await asyncio.to_thread(
            command.downgrade, migrated_scratch_database, PREVIOUS_REVISION
        )
