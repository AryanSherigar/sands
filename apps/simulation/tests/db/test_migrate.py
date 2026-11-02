import asyncio
from pathlib import Path

import pytest
from app.db.migrate import (
    MigrationFile,
    apply_migrations,
    compute_checksum,
    read_migration_files,
    select_pending_migrations,
)
from app.exceptions.migration_exceptions import (
    MigrationChecksumMismatchError,
    MigrationFileMissingError,
)
from psycopg import AsyncConnection
from psycopg.errors import UndefinedTable

EXPECTED_TABLES = {
    "sim_playthrough",
    "world_state",
    "world_snapshots",
    "turn_hashes",
    "event_log",
    "scenes",
    "model_answers",
    "schema_migrations",
    "simulation_operations",
    "battle_exchanges",
    "simulation_commands",
    "intent_requests",
    "simulation_replay_steps",
    "scene_exchanges",
    "summary_deliveries",
    "stance_requests",
    "art_deliveries",
    "dispatch_deliveries",
    "event_deliveries",
    "epilogue_deliveries",
}
SELECT_PUBLIC_TABLES = "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
SELECT_MIGRATION_ROWS = (
    "SELECT version, checksum FROM schema_migrations ORDER BY version"
)
FIRST_SQL = "CREATE TABLE first_table (id int PRIMARY KEY);"
SECOND_SQL = "CREATE TABLE second_table (id int PRIMARY KEY);"
BROKEN_SQL = (
    "CREATE TABLE third_table (id int PRIMARY KEY); SELECT * FROM missing_table;"
)


def _write(directory: Path, name: str, content: str) -> None:
    (directory / name).write_text(content)


def _file(version: str, content: str) -> MigrationFile:
    return MigrationFile(version, compute_checksum(content.encode()), content)


async def _fetch_column(database_url: str, query: str) -> list[str]:
    async with await AsyncConnection.connect(database_url) as connection:
        cursor = await connection.execute(query)
        return [row[0] for row in await cursor.fetchall()]


def test_files_are_read_in_prefix_order_and_others_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "0002_second.sql", SECOND_SQL)
    _write(tmp_path, "0001_first.sql", FIRST_SQL)
    _write(tmp_path, "notes.txt", "ignore me")
    assert [file.version for file in read_migration_files(tmp_path)] == [
        "0001_first",
        "0002_second",
    ]


def test_only_unapplied_files_are_pending() -> None:
    files = [_file("0001_a", FIRST_SQL), _file("0002_b", SECOND_SQL)]
    pending = select_pending_migrations(files, {"0001_a": files[0].checksum})
    assert [file.version for file in pending] == ["0002_b"]


def test_changed_checksum_is_refused() -> None:
    files = [_file("0001_a", FIRST_SQL)]
    with pytest.raises(MigrationChecksumMismatchError):
        select_pending_migrations(files, {"0001_a": "tampered"})


def test_missing_file_is_refused() -> None:
    with pytest.raises(MigrationFileMissingError):
        select_pending_migrations([], {"0001_a": "anything"})


async def test_files_apply_in_order_and_are_recorded(
    scratch_database_url: str, tmp_path: Path
) -> None:
    _write(tmp_path, "0001_first.sql", FIRST_SQL)
    _write(tmp_path, "0002_second.sql", SECOND_SQL)
    applied = await apply_migrations(scratch_database_url, tmp_path)
    assert applied == ["0001_first", "0002_second"]
    versions = await _fetch_column(scratch_database_url, SELECT_MIGRATION_ROWS)
    assert versions == ["0001_first", "0002_second"]


async def test_rerun_applies_nothing(scratch_database_url: str, tmp_path: Path) -> None:
    _write(tmp_path, "0001_first.sql", FIRST_SQL)
    await apply_migrations(scratch_database_url, tmp_path)
    assert await apply_migrations(scratch_database_url, tmp_path) == []


async def test_editing_an_applied_file_is_refused(
    scratch_database_url: str, tmp_path: Path
) -> None:
    _write(tmp_path, "0001_first.sql", FIRST_SQL)
    await apply_migrations(scratch_database_url, tmp_path)
    _write(tmp_path, "0001_first.sql", FIRST_SQL + " -- edited")
    _write(tmp_path, "0002_second.sql", SECOND_SQL)
    with pytest.raises(MigrationChecksumMismatchError):
        await apply_migrations(scratch_database_url, tmp_path)
    tables = await _fetch_column(scratch_database_url, SELECT_PUBLIC_TABLES)
    assert "second_table" not in tables


async def test_concurrent_runners_apply_each_file_once(
    scratch_database_url: str, tmp_path: Path
) -> None:
    _write(tmp_path, "0001_first.sql", FIRST_SQL)
    _write(tmp_path, "0002_second.sql", SECOND_SQL)
    first_run, second_run = await asyncio.gather(
        apply_migrations(scratch_database_url, tmp_path),
        apply_migrations(scratch_database_url, tmp_path),
    )
    assert sorted(first_run + second_run) == ["0001_first", "0002_second"]


async def test_failing_file_rolls_back_only_itself(
    scratch_database_url: str, tmp_path: Path
) -> None:
    _write(tmp_path, "0001_first.sql", FIRST_SQL)
    _write(tmp_path, "0002_broken.sql", BROKEN_SQL)
    with pytest.raises(UndefinedTable):
        await apply_migrations(scratch_database_url, tmp_path)
    versions = await _fetch_column(scratch_database_url, SELECT_MIGRATION_ROWS)
    tables = await _fetch_column(scratch_database_url, SELECT_PUBLIC_TABLES)
    assert versions == ["0001_first"]
    assert "third_table" not in tables


async def test_real_migrations_create_exactly_the_expected_tables(
    scratch_database_url: str,
) -> None:
    assert await apply_migrations(scratch_database_url) == [
        "0001_initial",
        "0002_battle_progress",
        "0003_command_acceptance_sequence",
        "0004_replay_steps",
        "0005_cancel_command_replay_step",
        "0006_scene_exchanges",
        "0006_summary_deliveries",
        "0007_scene_failed_attempts",
        "0008_stance_requests",
        "0009_art_deliveries",
        "0010_resolve_scene_replay_kind",
        "0011_dispatch_deliveries",
        "0012_scene_exchange_cited_grudges",
        "0013_event_deliveries",
        "0013_scene_exchange_verdict",
        "0014_epilogue_deliveries",
        "0015_battle_speech_replay_kinds",
        "0016_scene_exchange_clause_bands",
    ]
    tables = await _fetch_column(scratch_database_url, SELECT_PUBLIC_TABLES)
    assert set(tables) == EXPECTED_TABLES


async def test_db_connection_starts_with_empty_tables(db_connection) -> None:
    for table in ("sim_playthrough", "world_state", "event_log", "scenes"):
        cursor = await db_connection.execute(f"SELECT count(*) FROM {table}")
        assert await cursor.fetchone() == (0,)


async def test_original_migration_checksum_and_real_rerun(
    scratch_database_url: str,
) -> None:
    files = read_migration_files(Path("app/db/migrations"))
    assert (
        files[0].checksum
        == "27bfb2f3aef875a0b58a3a1e83510a1bf519a6105840bc355d92f475e197d373"
    )
    await apply_migrations(scratch_database_url)
    assert await apply_migrations(scratch_database_url) == []


async def test_battle_tables_have_scoped_keys_and_cascading_foreign_keys(
    scratch_database_url: str,
) -> None:
    await apply_migrations(scratch_database_url)
    query = """SELECT conrelid::regclass::text, contype, confdeltype
        FROM pg_constraint WHERE conrelid IN
        ('simulation_operations'::regclass, 'battle_exchanges'::regclass,
         'simulation_commands'::regclass, 'intent_requests'::regclass)"""
    async with await AsyncConnection.connect(scratch_database_url) as connection:
        cursor = await connection.execute(query)
        rows = await cursor.fetchall()
    for table in (
        "simulation_operations",
        "battle_exchanges",
        "simulation_commands",
        "intent_requests",
    ):
        assert (table, "p", " ") in rows
        assert (table, "f", "c") in rows
    assert sum(kind == "u" for _, kind, _ in rows) == 3


async def test_migration_preserves_existing_playthrough(
    scratch_database_url: str, tmp_path: Path
) -> None:
    initial = read_migration_files(Path("app/db/migrations"))[0]
    _write(tmp_path, initial.version + ".sql", initial.statements)
    await apply_migrations(scratch_database_url, tmp_path)
    async with await AsyncConnection.connect(
        scratch_database_url, autocommit=True
    ) as connection:
        await connection.execute(
            "INSERT INTO sim_playthrough (playthrough_id, owner_user_id, scenario, scenario_schema_version) VALUES ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', '{}', 1)"
        )
    assert await apply_migrations(scratch_database_url) == [
        "0002_battle_progress",
        "0003_command_acceptance_sequence",
        "0004_replay_steps",
        "0005_cancel_command_replay_step",
        "0006_scene_exchanges",
        "0006_summary_deliveries",
        "0007_scene_failed_attempts",
        "0008_stance_requests",
        "0009_art_deliveries",
        "0010_resolve_scene_replay_kind",
        "0011_dispatch_deliveries",
        "0012_scene_exchange_cited_grudges",
        "0013_event_deliveries",
        "0013_scene_exchange_verdict",
        "0014_epilogue_deliveries",
        "0015_battle_speech_replay_kinds",
        "0016_scene_exchange_clause_bands",
    ]
    assert await _fetch_column(
        scratch_database_url, "SELECT scenario_schema_version FROM sim_playthrough"
    ) == [1]


async def test_acceptance_migration_backfills_and_advances_sequence(
    scratch_database_url: str, tmp_path: Path
) -> None:
    for migration in read_migration_files(Path("app/db/migrations"))[:2]:
        _write(tmp_path, migration.version + ".sql", migration.statements)
    await apply_migrations(scratch_database_url, tmp_path)
    async with await AsyncConnection.connect(
        scratch_database_url, autocommit=True
    ) as connection:
        await _seed_legacy_commands(connection)
        assert await apply_migrations(scratch_database_url) == [
            "0003_command_acceptance_sequence",
            "0004_replay_steps",
            "0005_cancel_command_replay_step",
            "0006_scene_exchanges",
            "0006_summary_deliveries",
            "0007_scene_failed_attempts",
            "0008_stance_requests",
            "0009_art_deliveries",
            "0010_resolve_scene_replay_kind",
            "0011_dispatch_deliveries",
            "0012_scene_exchange_cited_grudges",
            "0013_event_deliveries",
            "0013_scene_exchange_verdict",
            "0014_epilogue_deliveries",
            "0015_battle_speech_replay_kinds",
            "0016_scene_exchange_clause_bands",
        ]
        assert await apply_migrations(scratch_database_url) == []
        cursor = await connection.execute(
            "SELECT command_id, acceptance_sequence FROM simulation_commands ORDER BY acceptance_sequence"
        )
        assert await cursor.fetchall() == [("later-uuid", 1), ("earlier-uuid", 2)]
        await _verify_migrated_sequence(connection)


async def _seed_legacy_commands(connection: AsyncConnection) -> None:
    await connection.execute(
        "INSERT INTO sim_playthrough (playthrough_id, owner_user_id, scenario, scenario_schema_version) VALUES ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', '{}', 1)"
    )
    await connection.execute("""INSERT INTO simulation_commands (playthrough_id, command_id, actor_id, operation_id, faction_id, accepted_turn, accepted_wave, execution_turn, reserved_cost, status, payload)
        VALUES ('11111111-1111-1111-1111-111111111111', 'earlier-uuid', 'owner', 'second', 'house_a', 1, 0, 1, 1, 'accepted', '{}'),
               ('11111111-1111-1111-1111-111111111111', 'later-uuid', 'owner', 'first', 'house_a', 0, 0, 0, 1, 'accepted', '{}')""")


async def _verify_migrated_sequence(connection: AsyncConnection) -> None:
    await connection.execute(
        "INSERT INTO simulation_commands (playthrough_id, command_id, actor_id, operation_id, faction_id, accepted_turn, accepted_wave, execution_turn, reserved_cost, status, payload) SELECT playthrough_id, 'new', actor_id, 'new', faction_id, 2, 0, 2, 1, 'accepted', '{}' FROM simulation_commands LIMIT 1"
    )
    cursor = await connection.execute(
        "SELECT acceptance_sequence FROM simulation_commands WHERE command_id = 'new'"
    )
    assert await cursor.fetchone() == (3,)
    cursor = await connection.execute(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'simulation_commands_acceptance_idx'"
    )
    assert (
        "(playthrough_id, actor_id, acceptance_sequence)"
        in (await cursor.fetchone())[0]
    )
