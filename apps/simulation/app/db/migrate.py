"""Forward-only SQL migration runner. Run as `python -m app.db.migrate`."""

import asyncio
import hashlib
from dataclasses import dataclass
from pathlib import Path

import structlog
from app.config import get_settings
from app.exceptions.migration_exceptions import (
    MigrationChecksumMismatchError,
    MigrationFileMissingError,
)
from psycopg import AsyncConnection

MIGRATIONS_DIRECTORY = Path(__file__).parent / "migrations"
MIGRATION_FILE_GLOB = "[0-9][0-9][0-9][0-9]_*.sql"
# NOTE: arbitrary but fixed; every runner must contend on the same key.
MIGRATION_ADVISORY_LOCK_KEY = 7_311_915_402

EVENT_MIGRATIONS_APPLIED = "migrations_applied"

CREATE_SCHEMA_MIGRATIONS = (
    "CREATE TABLE IF NOT EXISTS schema_migrations ("
    "version text PRIMARY KEY, "
    "checksum text NOT NULL, "
    "applied_at timestamptz NOT NULL DEFAULT now())"
)
SELECT_APPLIED_MIGRATIONS = "SELECT version, checksum FROM schema_migrations"
INSERT_APPLIED_MIGRATION = (
    "INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)"
)
ACQUIRE_ADVISORY_LOCK = "SELECT pg_advisory_lock(%s)"
RELEASE_ADVISORY_LOCK = "SELECT pg_advisory_unlock(%s)"


@dataclass(frozen=True)
class MigrationFile:
    version: str
    checksum: str
    statements: str


def compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def read_migration_files(directory: Path) -> list[MigrationFile]:
    """Files sorted by their zero-padded numeric prefix, i.e. apply order."""
    migration_files = []
    for path in sorted(directory.glob(MIGRATION_FILE_GLOB)):
        content = path.read_bytes()
        migration_files.append(
            MigrationFile(
                version=path.stem,
                checksum=compute_checksum(content),
                statements=content.decode("utf-8"),
            )
        )
    return migration_files


def select_pending_migrations(
    migration_files: list[MigrationFile], applied_checksums: dict[str, str]
) -> list[MigrationFile]:
    """Refuses the whole run if any applied file changed or vanished."""
    versions_on_disk = {migration.version for migration in migration_files}
    for version in applied_checksums:
        if version not in versions_on_disk:
            raise MigrationFileMissingError(version)
    for migration in migration_files:
        recorded_checksum = applied_checksums.get(migration.version)
        if recorded_checksum not in (None, migration.checksum):
            raise MigrationChecksumMismatchError(migration.version)
    return [
        migration
        for migration in migration_files
        if migration.version not in applied_checksums
    ]


async def _fetch_applied_checksums(connection: AsyncConnection) -> dict[str, str]:
    await connection.execute(CREATE_SCHEMA_MIGRATIONS)
    cursor = await connection.execute(SELECT_APPLIED_MIGRATIONS)
    rows = await cursor.fetchall()
    return {version: checksum for version, checksum in rows}


async def _apply_migration(
    connection: AsyncConnection, migration: MigrationFile
) -> None:
    async with connection.transaction():
        await connection.execute(migration.statements.encode("utf-8"))
        await connection.execute(
            INSERT_APPLIED_MIGRATION, (migration.version, migration.checksum)
        )


async def _apply_pending_migrations(
    connection: AsyncConnection, directory: Path
) -> list[str]:
    applied_checksums = await _fetch_applied_checksums(connection)
    pending = select_pending_migrations(
        read_migration_files(directory), applied_checksums
    )
    applied_versions = []
    for migration in pending:
        await _apply_migration(connection, migration)
        applied_versions.append(migration.version)
    return applied_versions


async def apply_migrations(
    database_url: str, directory: Path = MIGRATIONS_DIRECTORY
) -> list[str]:
    """Apply every pending migration under one advisory lock; return the versions applied.

    Each file runs in its own transaction. Raises MigrationChecksumMismatchError
    or MigrationFileMissingError before applying anything if history diverged.
    """
    async with await AsyncConnection.connect(
        database_url, autocommit=True
    ) as connection:
        await connection.execute(ACQUIRE_ADVISORY_LOCK, (MIGRATION_ADVISORY_LOCK_KEY,))
        try:
            return await _apply_pending_migrations(connection, directory)
        finally:
            await connection.execute(
                RELEASE_ADVISORY_LOCK, (MIGRATION_ADVISORY_LOCK_KEY,)
            )


def main() -> None:
    applied_versions = asyncio.run(
        apply_migrations(get_settings().simulation_database_url)
    )
    structlog.get_logger().info(
        EVENT_MIGRATIONS_APPLIED, applied_versions=applied_versions
    )


if __name__ == "__main__":
    main()
