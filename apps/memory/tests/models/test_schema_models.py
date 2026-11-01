"""Row models and Literal types must mirror the migrated schema exactly."""

import re
import typing
from uuid import uuid4

import pytest
from app.models import common
from app.models.evidence import EventRow, SourceRow, SpanRow
from app.models.facts import (
    AliasRow,
    CommitmentRow,
    CommitmentStatusRow,
    EntityRow,
    FactRow,
    FactSourceRow,
    SceneStateRow,
    SupersessionRow,
)
from app.models.jobs import (
    EmbeddingFailureRow,
    EmbeddingModelRow,
    EmbeddingRow,
    ExtractionBatchRow,
)
from app.models.templates import PlaythroughRow, TemplateRow
from pgvector import Vector
from psycopg import AsyncConnection
from pydantic import BaseModel

ROW_MODEL_BY_TABLE: dict[str, type[BaseModel]] = {
    "memory_template": TemplateRow,
    "memory_playthrough": PlaythroughRow,
    "memory_source": SourceRow,
    "memory_span": SpanRow,
    "memory_event": EventRow,
    "memory_entity": EntityRow,
    "memory_alias": AliasRow,
    "memory_fact": FactRow,
    "memory_fact_source": FactSourceRow,
    "memory_supersession": SupersessionRow,
    "memory_commitment": CommitmentRow,
    "memory_commitment_status": CommitmentStatusRow,
    "memory_scene_state": SceneStateRow,
    "memory_embedding": EmbeddingRow,
    "memory_embedding_model": EmbeddingModelRow,
    "memory_embedding_failure": EmbeddingFailureRow,
    "memory_extraction_batch": ExtractionBatchRow,
}

LITERAL_BY_CHECKED_COLUMN: dict[tuple[str, str], object] = {
    ("memory_template", "mode"): common.TemplateMode,
    ("memory_template", "direct_status"): common.TemplateDirectStatus,
    ("memory_template", "enrichment_status"): common.TemplateEnrichmentStatus,
    ("memory_source", "source_kind"): common.SourceKind,
    ("memory_event", "event_kind"): common.EventKind,
    ("memory_entity", "provenance"): common.EntityProvenance,
    ("memory_fact", "authority"): common.Authority,
    ("memory_fact", "assertion"): common.Assertion,
    ("memory_supersession", "authority"): common.Authority,
    ("memory_commitment", "kind"): common.CommitmentKind,
    ("memory_commitment_status", "status"): common.CommitmentStatusValue,
    ("memory_embedding", "target_kind"): common.EmbeddingTargetKind,
    ("memory_embedding_failure", "target_kind"): common.EmbeddingTargetKind,
    ("memory_extraction_batch", "status"): common.ExtractionBatchStatus,
}

SELECT_TABLE_COLUMNS = (
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_schema = 'public' AND table_name = %s"
)
SELECT_SINGLE_COLUMN_CHECKS = (
    "SELECT rel.relname, att.attname, pg_get_constraintdef(con.oid) "
    "FROM pg_constraint con "
    "JOIN pg_class rel ON rel.oid = con.conrelid "
    "JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = con.conkey[1] "
    "WHERE con.contype = 'c' AND cardinality(con.conkey) = 1 "
    "AND rel.relname LIKE 'memory\\_%%' AND pg_get_constraintdef(con.oid) LIKE '%%ANY%%'"
)
QUOTED_TEXT_LITERAL = re.compile(r"'([^']+)'::text")


@pytest.mark.parametrize("table_name", sorted(ROW_MODEL_BY_TABLE))
async def test_row_model_fields_equal_table_columns(
    db_connection: AsyncConnection, table_name: str
) -> None:
    cursor = await db_connection.execute(SELECT_TABLE_COLUMNS, (table_name,))
    columns = {row[0] for row in await cursor.fetchall()}

    assert set(ROW_MODEL_BY_TABLE[table_name].model_fields) == columns


async def test_literal_types_equal_enumerated_checks(
    db_connection: AsyncConnection,
) -> None:
    cursor = await db_connection.execute(SELECT_SINGLE_COLUMN_CHECKS)
    checks = {
        (table, column): set(QUOTED_TEXT_LITERAL.findall(definition))
        for table, column, definition in await cursor.fetchall()
    }
    scope_kind_columns = {key for key in checks if key[1] == "scope_kind"}
    expected = {
        key: set(typing.get_args(literal))
        for key, literal in LITERAL_BY_CHECKED_COLUMN.items()
    }
    expected.update(
        {key: set(typing.get_args(common.ScopeKind)) for key in scope_kind_columns}
    )

    assert checks == expected
    assert len(scope_kind_columns) == 7


def test_embedding_row_accepts_pgvector_value() -> None:
    row = EmbeddingRow(
        target_kind="span",
        target_id=uuid4(),
        scope_kind="playthrough",
        scope_id=uuid4(),
        model="model",
        model_version="1",
        dim=2,
        embedding=Vector([0.5, 0.25]),
        content_hash="hash",
        created_at="2026-10-27T00:00:00Z",
    )

    assert row.embedding == [0.5, 0.25]
