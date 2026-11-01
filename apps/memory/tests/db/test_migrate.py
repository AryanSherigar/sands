"""Migration runner and 0001_initial schema tests against a real PG18 database."""

import asyncio
import hashlib
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from app.db.migrate import apply_migrations
from app.exceptions.migration_exceptions import MigrationChecksumMismatchError
from pgvector import Vector
from psycopg import AsyncConnection

MIGRATIONS_DIRECTORY = Path(__file__).parents[2] / "app" / "db" / "migrations"
INITIAL_VERSION = "0001_initial"
ALIAS_SCOPE_PK_VERSION = "0002_alias_scope_pk"
FACT_SUPERSEDES_VERSION = "0003_fact_supersedes_authored"
EMBEDDING_FAILURE_VERSION = "0004_embedding_failure"
PROCRASTINATE_VERSION = "0005_procrastinate_schema"
EXTRACTION_CONTEXT_VERSION = "0006_extraction_context"
INGEST_DELIVERY_VERSION = "0007_ingest_delivery"
ALL_VERSIONS = [
    INITIAL_VERSION,
    ALIAS_SCOPE_PK_VERSION,
    FACT_SUPERSEDES_VERSION,
    EMBEDDING_FAILURE_VERSION,
    PROCRASTINATE_VERSION,
    EXTRACTION_CONTEXT_VERSION,
    INGEST_DELIVERY_VERSION,
]

EXPECTED_MEMORY_TABLES = frozenset(
    {
        "memory_template",
        "memory_playthrough",
        "memory_source",
        "memory_span",
        "memory_event",
        "memory_entity",
        "memory_alias",
        "memory_fact",
        "memory_fact_source",
        "memory_supersession",
        "memory_commitment",
        "memory_commitment_status",
        "memory_scene_state",
        "memory_embedding",
        "memory_embedding_model",
        "memory_embedding_failure",
        "memory_extraction_batch",
        "memory_ingest_delivery",
        "memory_purged_playthrough",
    }
)
PROCRASTINATE_TABLES = frozenset(
    {
        "procrastinate_jobs",
        "procrastinate_events",
        "procrastinate_periodic_defers",
        "procrastinate_workers",
    }
)

SELECT_PUBLIC_TABLES = "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
SELECT_EXTENSIONS = "SELECT extname FROM pg_extension"
SELECT_MIGRATION_ROWS = "SELECT version, checksum FROM schema_migrations"
TAMPER_CHECKSUM = (
    "UPDATE schema_migrations SET checksum = 'tampered' WHERE version = %s"
)

INSERT_EMBEDDING_MODEL = (
    "INSERT INTO memory_embedding_model (model, model_version, dim, is_active) "
    "VALUES (%s, %s, %s, %s)"
)
INSERT_EMBEDDING = (
    "INSERT INTO memory_embedding (target_kind, target_id, scope_kind, scope_id, "
    "model, model_version, dim, embedding, content_hash) "
    "VALUES ('span', %s, 'playthrough', %s, %s, %s, %s, %s, 'hash')"
)
INSERT_SOURCE_WITH_SCOPE_KIND = (
    "INSERT INTO memory_source (scope_kind, scope_id, source_kind, source_ref, "
    "sequence, content, content_hash) "
    "VALUES (%s, %s, 'turn_action', 'turn-1', 1, 'text', 'hash')"
)
INSERT_PLAYTHROUGH = "INSERT INTO memory_playthrough (playthrough_id) VALUES (%s)"
INSERT_EVENT = (
    "INSERT INTO memory_event (playthrough_id, sequence, turn_id, event_kind, "
    "event_key, is_accepted, payload) "
    "VALUES (%s, 1, %s, 'roll', 'roll-1', true, '{}'::jsonb)"
)
DELETE_PLAYTHROUGH = "DELETE FROM memory_playthrough WHERE playthrough_id = %s"
COUNT_EVENTS_FOR_PLAYTHROUGH = (
    "SELECT count(*) FROM memory_event WHERE playthrough_id = %s"
)

MODEL_NAME = "test-embedder"
MODEL_VERSION = "1"
MODEL_DIM = 3


async def _fetch_first_column(database_url: str, query: str) -> set[str]:
    async with await AsyncConnection.connect(database_url) as connection:
        cursor = await connection.execute(query)
        rows = await cursor.fetchall()
    return {row[0] for row in rows}


def _file_checksum(version: str) -> str:
    content = (MIGRATIONS_DIRECTORY / f"{version}.sql").read_bytes()
    return hashlib.sha256(content).hexdigest()


async def test_empty_database_gets_every_table_and_both_extensions(
    scratch_database_url: str,
) -> None:
    applied_versions = await apply_migrations(scratch_database_url)

    assert applied_versions == ALL_VERSIONS
    tables = await _fetch_first_column(scratch_database_url, SELECT_PUBLIC_TABLES)
    assert tables == EXPECTED_MEMORY_TABLES | PROCRASTINATE_TABLES | {
        "schema_migrations"
    }
    extensions = await _fetch_first_column(scratch_database_url, SELECT_EXTENSIONS)
    assert {"vector", "pg_textsearch"} <= extensions


async def test_applied_migration_is_recorded_with_its_checksum(
    scratch_database_url: str,
) -> None:
    await apply_migrations(scratch_database_url)

    async with await AsyncConnection.connect(scratch_database_url) as connection:
        cursor = await connection.execute(SELECT_MIGRATION_ROWS)
        rows = await cursor.fetchall()

    assert rows == [(version, _file_checksum(version)) for version in ALL_VERSIONS]


async def test_rerun_applies_nothing(scratch_database_url: str) -> None:
    await apply_migrations(scratch_database_url)

    assert await apply_migrations(scratch_database_url) == []


async def test_changed_checksum_of_applied_file_refuses_to_run(
    scratch_database_url: str,
) -> None:
    await apply_migrations(scratch_database_url)
    async with await AsyncConnection.connect(
        scratch_database_url, autocommit=True
    ) as connection:
        await connection.execute(TAMPER_CHECKSUM, (INITIAL_VERSION,))

    with pytest.raises(MigrationChecksumMismatchError):
        await apply_migrations(scratch_database_url)


async def test_concurrent_runs_serialize_and_apply_once(
    scratch_database_url: str,
) -> None:
    first_run, second_run = await asyncio.gather(
        apply_migrations(scratch_database_url),
        apply_migrations(scratch_database_url),
    )

    assert sorted(first_run + second_run) == ALL_VERSIONS


async def _insert_embedding_model(
    connection: AsyncConnection, model_version: str, is_active: bool
) -> None:
    await connection.execute(
        INSERT_EMBEDDING_MODEL, (MODEL_NAME, model_version, MODEL_DIM, is_active)
    )


async def test_embedding_with_wrong_vector_length_fails_check(
    db_connection: AsyncConnection,
) -> None:
    await _insert_embedding_model(db_connection, MODEL_VERSION, is_active=True)
    wrong_length_vector = Vector([0.1] * (MODEL_DIM + 1))

    with pytest.raises(psycopg.errors.CheckViolation):
        await db_connection.execute(
            INSERT_EMBEDDING,
            (
                uuid4(),
                uuid4(),
                MODEL_NAME,
                MODEL_VERSION,
                MODEL_DIM,
                wrong_length_vector,
            ),
        )


async def test_embedding_with_matching_vector_length_round_trips(
    db_connection: AsyncConnection,
) -> None:
    await _insert_embedding_model(db_connection, MODEL_VERSION, is_active=True)
    vector = Vector([0.5] * MODEL_DIM)
    await db_connection.execute(
        INSERT_EMBEDDING,
        (uuid4(), uuid4(), MODEL_NAME, MODEL_VERSION, MODEL_DIM, vector),
    )

    cursor = await db_connection.execute("SELECT embedding FROM memory_embedding")
    row = await cursor.fetchone()

    assert row is not None
    assert row[0] == vector


async def test_two_active_embedding_models_violate_partial_unique_index(
    db_connection: AsyncConnection,
) -> None:
    await _insert_embedding_model(db_connection, "1", is_active=True)

    with pytest.raises(psycopg.errors.UniqueViolation):
        await _insert_embedding_model(db_connection, "2", is_active=True)


async def test_inactive_embedding_models_may_coexist(
    db_connection: AsyncConnection,
) -> None:
    await _insert_embedding_model(db_connection, "1", is_active=True)
    await _insert_embedding_model(db_connection, "2", is_active=False)
    await _insert_embedding_model(db_connection, "3", is_active=False)


async def test_unknown_scope_kind_fails_check(db_connection: AsyncConnection) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        await db_connection.execute(INSERT_SOURCE_WITH_SCOPE_KIND, ("other", uuid4()))


async def test_deleting_playthrough_cascades_to_its_events(
    db_connection: AsyncConnection,
) -> None:
    playthrough_id: UUID = uuid4()
    await db_connection.execute(INSERT_PLAYTHROUGH, (playthrough_id,))
    await db_connection.execute(INSERT_EVENT, (playthrough_id, uuid4()))

    await db_connection.execute(DELETE_PLAYTHROUGH, (playthrough_id,))
    cursor = await db_connection.execute(
        COUNT_EVENTS_FOR_PLAYTHROUGH, (playthrough_id,)
    )
    row = await cursor.fetchone()

    assert row == (0,)


async def test_db_connection_starts_with_empty_memory_tables(
    db_connection: AsyncConnection,
) -> None:
    cursor = await db_connection.execute("SELECT count(*) FROM memory_embedding_model")

    assert await cursor.fetchone() == (0,)


INSERT_TEMPLATE_SCOPE_ENTITY = """
INSERT INTO memory_entity
    (scope_kind, scope_id, entity_type, canonical_name, provenance, first_seen_seq)
VALUES ('template', %s, 'character', 'Mira', 'authored', 0)
RETURNING entity_id
"""

INSERT_AUTHORED_FACT = """
INSERT INTO memory_fact
    (scope_kind, scope_id, subject_entity_id, predicate, authority, assertion,
     valid_from_seq, authored_fact_id)
VALUES ('template', %s, %s, 'is_a', 'authored', 'occurred', 0, %s)
"""


async def _insert_template_entity(
    db_connection: AsyncConnection, scope_id: UUID
) -> UUID:
    cursor = await db_connection.execute(INSERT_TEMPLATE_SCOPE_ENTITY, (scope_id,))
    row = await cursor.fetchone()
    assert row is not None
    return row[0]


async def test_authored_fact_is_unique_per_scope(
    db_connection: AsyncConnection,
) -> None:
    scope_id, authored_fact_id = uuid4(), uuid4()
    entity_id = await _insert_template_entity(db_connection, scope_id)
    await db_connection.execute(
        INSERT_AUTHORED_FACT, (scope_id, entity_id, authored_fact_id)
    )

    with pytest.raises(psycopg.errors.UniqueViolation):
        await db_connection.execute(
            INSERT_AUTHORED_FACT, (scope_id, entity_id, authored_fact_id)
        )


async def test_facts_without_authored_id_are_not_constrained(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    entity_id = await _insert_template_entity(db_connection, scope_id)

    await db_connection.execute(INSERT_AUTHORED_FACT, (scope_id, entity_id, None))
    await db_connection.execute(INSERT_AUTHORED_FACT, (scope_id, entity_id, None))
