"""Fake embedder, settings and data builders for indexing_service tests."""

import asyncio
import hashlib
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.config import Settings
from app.exceptions.indexing_exceptions import (
    EmbeddingAnomalyError,
    EmbeddingPermanentError,
)
from app.models.common import ScopeKind
from app.models.evidence import SourceCreate
from app.models.facts import EntityCreate, FactCreate
from app.repositories import (
    entity_repo,
    fact_repo,
    playthrough_repo,
    source_repo,
    span_repo,
)
from psycopg import AsyncConnection
from tests.repositories.helpers_evidence import (
    build_span,
    make_playthrough,
    make_template,
)

TEST_DIM = 8
MODEL_A = ("model-a", "1")
MODEL_B = ("model-b", "1")
POISON_MARKER = "POISON"
COUNT_EMBEDDINGS_SQL = (
    "SELECT count(*) FROM memory_embedding WHERE model = %s AND model_version = %s"
)
SELECT_INDEXED_SEQ_SQL = (
    "SELECT indexed_seq FROM memory_playthrough WHERE playthrough_id = %s"
)
SELECT_ACTIVE_MODEL_SQL = (
    "SELECT model, model_version FROM memory_embedding_model WHERE is_active"
)
SELECT_MODEL_ROWS_SQL = (
    "SELECT model, model_version, is_active FROM memory_embedding_model ORDER BY model"
)
SELECT_EMBEDDED_IDS_SQL = (
    "SELECT target_id FROM memory_embedding WHERE model = %s AND model_version = %s"
)


def make_settings(model: tuple[str, str] = MODEL_A, **overrides: int | str) -> Settings:
    values: dict[str, int | str] = {
        "embedding_api_key": "test-key",
        "embedding_model_name": model[0],
        "embedding_model_version": model[1],
        "embedding_dim": TEST_DIM,
        "embedding_claim_size": 50,
        "embedding_batch_size": 10,
        "embedding_concurrency": 2,
        "embedding_failure_limit": 3,
        "process_pending_deadline_seconds": 30,
    }
    values.update(overrides)
    return Settings(**values)


def vector_for(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [(byte + 1) / 256 for byte in digest[:TEST_DIM]]


class FakeEmbedder:
    """Deterministic DocumentEmbedder recording every call; failures are scripted."""

    def __init__(self, delay_seconds: float = 0.0) -> None:
        self.calls: list[list[str]] = []
        self.deadlines: list[float | None] = []
        self._delay_seconds = delay_seconds
        self._errors_by_call: dict[int, Exception] = {}
        self._wrong_count_calls: set[int] = set()

    def raise_on_call(self, call_number: int, error: Exception) -> None:
        self._errors_by_call[call_number] = error

    def return_wrong_count_on_call(self, call_number: int) -> None:
        self._wrong_count_calls.add(call_number)

    @property
    def texts(self) -> list[str]:
        return [text for call in self.calls for text in call]

    async def embed_documents(
        self, texts: list[str], deadline_monotonic: float | None = None
    ) -> list[list[float]]:
        self.calls.append(list(texts))
        self.deadlines.append(deadline_monotonic)
        call_number = len(self.calls)
        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)
        if call_number in self._errors_by_call:
            raise self._errors_by_call[call_number]
        if any(POISON_MARKER in text for text in texts):
            raise EmbeddingPermanentError()
        if call_number in self._wrong_count_calls:
            return [vector_for(text) for text in texts[:-1]]
        return [vector_for(text) for text in texts]


def dimension_mismatch_error() -> EmbeddingAnomalyError:
    return EmbeddingAnomalyError(is_dimension_mismatch=True)


@dataclass(frozen=True)
class World:
    template_id: UUID
    playthrough_id: UUID


async def make_world(connection: AsyncConnection) -> World:
    template = await make_template(connection)
    playthrough = await make_playthrough(connection, template_id=template.template_id)
    await connection.commit()
    return World(template.template_id, playthrough.playthrough_id)


async def add_span(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    sequence: int,
    text: str,
    *,
    is_hidden: bool = False,
    conditional: bool = False,
) -> UUID:
    source = await source_repo.create_source(
        connection,
        SourceCreate(
            scope_kind=scope_kind,
            scope_id=scope_id,
            source_kind="turn_narration",
            source_ref=str(uuid4()),
            sequence=sequence,
            content=text,
            content_hash="hash",
        ),
    )
    draft = build_span(
        source_id=source.source_id,
        scope_kind=scope_kind,
        scope_id=scope_id,
        sequence=sequence,
        text=text,
    )
    draft.is_hidden = is_hidden
    draft.conditional = conditional
    rows = await span_repo.create_spans(connection, [draft])
    await connection.commit()
    return rows[0].span_id


async def add_fact(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    subject_name: str,
    literal: str,
    *,
    valid_from_seq: int = 1,
    is_hidden: bool = False,
    conditional: bool = False,
) -> UUID:
    subject = await entity_repo.create_entity(
        connection,
        EntityCreate(
            scope_kind=scope_kind,
            scope_id=scope_id,
            entity_type="character",
            canonical_name=subject_name,
            provenance="extracted",
            first_seen_seq=0,
        ),
    )
    rows = await fact_repo.create_facts(
        connection,
        [
            FactCreate(
                scope_kind=scope_kind,
                scope_id=scope_id,
                subject_entity_id=subject.entity_id,
                predicate="serves",
                object_literal=literal,
                authority="extracted",
                assertion="occurred",
                valid_from_seq=valid_from_seq,
                is_hidden=is_hidden,
                conditional=conditional,
            )
        ],
    )
    await connection.commit()
    return rows[0].fact_id


async def set_ingested_seq(
    connection: AsyncConnection, playthrough_id: UUID, sequence: int
) -> None:
    await playthrough_repo.advance_watermarks(
        connection, playthrough_id, ingested_seq=sequence
    )
    await connection.commit()


async def read_indexed_seq(connection: AsyncConnection, playthrough_id: UUID) -> int:
    cursor = await connection.execute(SELECT_INDEXED_SEQ_SQL, (playthrough_id,))
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def count_embeddings(
    connection: AsyncConnection, model: tuple[str, str] = MODEL_A
) -> int:
    cursor = await connection.execute(COUNT_EMBEDDINGS_SQL, model)
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def read_embedded_ids(
    connection: AsyncConnection, model: tuple[str, str] = MODEL_A
) -> set[UUID]:
    cursor = await connection.execute(SELECT_EMBEDDED_IDS_SQL, model)
    return {row[0] for row in await cursor.fetchall()}


async def read_active_model(connection: AsyncConnection) -> tuple[str, str] | None:
    cursor = await connection.execute(SELECT_ACTIVE_MODEL_SQL)
    row = await cursor.fetchone()
    return None if row is None else (row[0], row[1])


async def read_model_rows(
    connection: AsyncConnection,
) -> list[tuple[str, str, bool]]:
    cursor = await connection.execute(SELECT_MODEL_ROWS_SQL)
    return [(row[0], row[1], row[2]) for row in await cursor.fetchall()]
