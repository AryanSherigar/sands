"""Repository for memory_embedding and memory_embedding_model (child table)."""

from uuid import UUID

from app.models.common import ScopeKind
from app.models.eligibility import EligibilityContext
from app.models.jobs import (
    EmbeddingCreate,
    EmbeddingModelCreate,
    EmbeddingModelRow,
    EmbeddingRow,
    FactClaimRow,
    SpanClaimRow,
)
from app.models.retrieval_rows import VectorHit
from app.repositories.eligibility_predicates import (
    FACT_ELIGIBLE,
    SPAN_ELIGIBLE,
    scope_predicate,
)
from pgvector import Vector
from psycopg import AsyncConnection, AsyncCursor
from psycopg.rows import class_row

REGISTER_EMBEDDING_MODEL_SQL = """
INSERT INTO memory_embedding_model (model, model_version, dim, is_active)
VALUES (%(model)s, %(model_version)s, %(dim)s, %(is_active)s)
ON CONFLICT (model, model_version) DO NOTHING
RETURNING *
"""

SELECT_EMBEDDING_MODEL_SQL = """
SELECT * FROM memory_embedding_model
WHERE model = %(model)s AND model_version = %(model_version)s
"""

GET_ACTIVE_EMBEDDING_MODEL_SQL = (
    "SELECT * FROM memory_embedding_model WHERE is_active LIMIT 1"
)

DEACTIVATE_CURRENT_MODEL_SQL = (
    "UPDATE memory_embedding_model SET is_active = false WHERE is_active"
)

ACTIVATE_MODEL_SQL = """
UPDATE memory_embedding_model
SET is_active = true
WHERE model = %(model)s AND model_version = %(model_version)s
RETURNING *
"""

CREATE_EMBEDDING_SQL = """
INSERT INTO memory_embedding (
    target_kind, target_id, scope_kind, scope_id, model, model_version, dim, embedding, content_hash
) VALUES (
    %(target_kind)s, %(target_id)s, %(scope_kind)s, %(scope_id)s, %(model)s,
    %(model_version)s, %(dim)s, %(embedding)s, %(content_hash)s
)
ON CONFLICT (target_kind, target_id, model, model_version) DO NOTHING
RETURNING *
"""

SELECT_EMBEDDING_SQL = """
SELECT * FROM memory_embedding
WHERE target_kind = %(target_kind)s AND target_id = %(target_id)s
    AND model = %(model)s AND model_version = %(model_version)s
"""

LIST_EMBEDDINGS_FOR_ACTIVE_MODEL_SQL = """
SELECT e.*
FROM memory_embedding AS e
JOIN memory_embedding_model AS m ON m.model = e.model AND m.model_version = e.model_version
WHERE m.is_active AND e.scope_kind = %(scope_kind)s AND e.scope_id = %(scope_id)s
"""

STORED_EMBEDDING_MATCH = f"""
stored.model = %(model)s AND stored.model_version = %(model_version)s
    AND stored.dim = %(dim)s::integer
    AND {scope_predicate("stored")}
"""

SEARCH_ELIGIBLE_EMBEDDINGS_SQL = f"""
SELECT target_kind, target_id, distance FROM (
    SELECT stored.target_kind, stored.target_id,
        stored.embedding <=> %(query_vector)s::vector AS distance
    FROM memory_embedding AS stored
    JOIN memory_span AS span
        ON stored.target_kind = 'span' AND stored.target_id = span.span_id
    WHERE {STORED_EMBEDDING_MATCH} AND {SPAN_ELIGIBLE}
    UNION ALL
    SELECT stored.target_kind, stored.target_id,
        stored.embedding <=> %(query_vector)s::vector AS distance
    FROM memory_embedding AS stored
    JOIN memory_fact AS fact
        ON stored.target_kind = 'fact' AND stored.target_id = fact.fact_id
    WHERE {STORED_EMBEDDING_MATCH} AND {FACT_ELIGIBLE}
) AS hits
ORDER BY distance, target_id
LIMIT %(limit)s
"""

UNCOVERED_TARGET_PREDICATE = """
NOT EXISTS (
    SELECT 1 FROM memory_embedding AS existing
    WHERE existing.target_kind = '{kind}' AND existing.target_id = {alias}.{id_column}
        AND existing.model = %(model)s AND existing.model_version = %(model_version)s
)
AND NOT EXISTS (
    SELECT 1 FROM memory_embedding_failure AS failure
    WHERE failure.target_kind = '{kind}' AND failure.target_id = {alias}.{id_column}
        AND failure.model = %(model)s AND failure.model_version = %(model_version)s
        AND failure.attempt_count >= %(failure_limit)s
)
"""

SCOPE_FILTER_PREDICATE = """
(
    %(playthrough_id)s::uuid IS NULL
    OR ({alias}.scope_kind = 'playthrough' AND {alias}.scope_id = %(playthrough_id)s::uuid)
)
"""

CLAIM_UNEMBEDDED_SPANS_SQL = f"""
SELECT s.span_id, s.scope_kind, s.scope_id, s.text
FROM memory_span AS s
WHERE {SCOPE_FILTER_PREDICATE.format(alias="s")}
    AND {UNCOVERED_TARGET_PREDICATE.format(kind="span", alias="s", id_column="span_id")}
ORDER BY (s.scope_kind = 'playthrough') DESC, s.sequence ASC, s.span_id ASC
LIMIT %(limit)s
FOR UPDATE OF s SKIP LOCKED
"""

CLAIM_UNEMBEDDED_FACTS_SQL = f"""
SELECT f.fact_id, f.scope_kind, f.scope_id, subject.canonical_name AS subject_name,
    f.predicate, COALESCE(object.canonical_name, f.object_literal) AS object_text
FROM memory_fact AS f
JOIN memory_entity AS subject ON subject.entity_id = f.subject_entity_id
LEFT JOIN memory_entity AS object ON object.entity_id = f.object_entity_id
WHERE {SCOPE_FILTER_PREDICATE.format(alias="f")}
    AND {UNCOVERED_TARGET_PREDICATE.format(kind="fact", alias="f", id_column="fact_id")}
ORDER BY (f.scope_kind = 'playthrough') DESC, f.valid_from_seq ASC, f.fact_id ASC
LIMIT %(limit)s
FOR UPDATE OF f SKIP LOCKED
"""

INSERT_EMBEDDING_SQL = """
INSERT INTO memory_embedding (
    target_kind, target_id, scope_kind, scope_id, model, model_version, dim, embedding, content_hash
) VALUES (
    %(target_kind)s, %(target_id)s, %(scope_kind)s, %(scope_id)s, %(model)s,
    %(model_version)s, %(dim)s, %(embedding)s, %(content_hash)s
)
ON CONFLICT (target_kind, target_id, model, model_version) DO NOTHING
"""

COUNT_UNCOVERED_TARGETS_SQL = f"""
SELECT
    (
        SELECT count(*) FROM memory_span AS s
        WHERE {UNCOVERED_TARGET_PREDICATE.format(kind="span", alias="s", id_column="span_id")}
    ) + (
        SELECT count(*) FROM memory_fact AS f
        WHERE {UNCOVERED_TARGET_PREDICATE.format(kind="fact", alias="f", id_column="fact_id")}
    )
"""

DELETE_EMBEDDINGS_EXCEPT_MODELS_SQL = """
DELETE FROM memory_embedding AS e
WHERE NOT EXISTS (
    SELECT 1
    FROM unnest(%(models)s::text[], %(model_versions)s::text[]) AS kept (model, model_version)
    WHERE kept.model = e.model AND kept.model_version = e.model_version
)
"""


async def register_embedding_model(
    connection: AsyncConnection, model: EmbeddingModelCreate
) -> EmbeddingModelRow:
    async with connection.cursor(row_factory=class_row(EmbeddingModelRow)) as cursor:
        await cursor.execute(REGISTER_EMBEDDING_MODEL_SQL, model.model_dump())
        row = await cursor.fetchone()
        if row is not None:
            return row
        await cursor.execute(
            SELECT_EMBEDDING_MODEL_SQL,
            {"model": model.model, "model_version": model.model_version},
        )
        existing = await cursor.fetchone()
    if existing is None:
        raise RuntimeError(
            "Embedding model insert conflicted but no existing row was found."
        )
    return existing


async def get_active_embedding_model(
    connection: AsyncConnection,
) -> EmbeddingModelRow | None:
    async with connection.cursor(row_factory=class_row(EmbeddingModelRow)) as cursor:
        await cursor.execute(GET_ACTIVE_EMBEDDING_MODEL_SQL)
        return await cursor.fetchone()


async def activate_embedding_model(
    connection: AsyncConnection, model: str, model_version: str
) -> EmbeddingModelRow:
    async with connection.cursor(row_factory=class_row(EmbeddingModelRow)) as cursor:
        await cursor.execute(DEACTIVATE_CURRENT_MODEL_SQL)
        await cursor.execute(
            ACTIVATE_MODEL_SQL, {"model": model, "model_version": model_version}
        )
        row = await cursor.fetchone()
    if row is None:
        raise RuntimeError(
            f"No embedding model registered for {model} {model_version}."
        )
    return row


async def _insert_or_get_embedding(
    cursor: AsyncCursor[EmbeddingRow], embedding: EmbeddingCreate
) -> EmbeddingRow:
    params = embedding.model_dump()
    params["embedding"] = Vector(embedding.embedding)
    await cursor.execute(CREATE_EMBEDDING_SQL, params)
    row = await cursor.fetchone()
    if row is not None:
        return row
    await cursor.execute(
        SELECT_EMBEDDING_SQL,
        {
            "target_kind": embedding.target_kind,
            "target_id": embedding.target_id,
            "model": embedding.model,
            "model_version": embedding.model_version,
        },
    )
    existing = await cursor.fetchone()
    if existing is None:
        raise RuntimeError("Embedding insert conflicted but no existing row was found.")
    return existing


async def create_embeddings(
    connection: AsyncConnection, embeddings: list[EmbeddingCreate]
) -> list[EmbeddingRow]:
    rows: list[EmbeddingRow] = []
    async with connection.cursor(row_factory=class_row(EmbeddingRow)) as cursor:
        for embedding in embeddings:
            rows.append(await _insert_or_get_embedding(cursor, embedding))
    return rows


async def list_embeddings_for_active_model(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> list[EmbeddingRow]:
    async with connection.cursor(row_factory=class_row(EmbeddingRow)) as cursor:
        await cursor.execute(
            LIST_EMBEDDINGS_FOR_ACTIVE_MODEL_SQL,
            {"scope_kind": scope_kind, "scope_id": scope_id},
        )
        return await cursor.fetchall()


def _claim_params(
    model: str,
    model_version: str,
    limit: int,
    failure_limit: int,
    playthrough_id: UUID | None,
) -> dict[str, object]:
    return {
        "model": model,
        "model_version": model_version,
        "limit": limit,
        "failure_limit": failure_limit,
        "playthrough_id": playthrough_id,
    }


async def claim_unembedded_spans(
    connection: AsyncConnection,
    model: str,
    model_version: str,
    limit: int,
    failure_limit: int,
    playthrough_id: UUID | None,
) -> list[SpanClaimRow]:
    """Locks the claimed span rows until the caller's transaction ends.

    Playthrough scope first, then lowest sequence. SKIP LOCKED is applied before
    LIMIT, so a concurrent claimer receives the next unlocked rows, not fewer.
    """
    params = _claim_params(model, model_version, limit, failure_limit, playthrough_id)
    async with connection.cursor(row_factory=class_row(SpanClaimRow)) as cursor:
        await cursor.execute(CLAIM_UNEMBEDDED_SPANS_SQL, params)
        return await cursor.fetchall()


async def claim_unembedded_facts(
    connection: AsyncConnection,
    model: str,
    model_version: str,
    limit: int,
    failure_limit: int,
    playthrough_id: UUID | None,
) -> list[FactClaimRow]:
    """Same contract as claim_unembedded_spans; only the fact row is locked."""
    params = _claim_params(model, model_version, limit, failure_limit, playthrough_id)
    async with connection.cursor(row_factory=class_row(FactClaimRow)) as cursor:
        await cursor.execute(CLAIM_UNEMBEDDED_FACTS_SQL, params)
        return await cursor.fetchall()


async def insert_embeddings(
    connection: AsyncConnection, embeddings: list[EmbeddingCreate]
) -> int:
    """Returns the number of rows actually inserted; conflicting rows are skipped."""
    if not embeddings:
        return 0
    params = []
    for embedding in embeddings:
        row_params = embedding.model_dump()
        row_params["embedding"] = Vector(embedding.embedding)
        params.append(row_params)
    async with connection.cursor() as cursor:
        await cursor.executemany(INSERT_EMBEDDING_SQL, params)
        return cursor.rowcount


async def count_uncovered_targets(
    connection: AsyncConnection,
    model: str,
    model_version: str,
    failure_limit: int,
) -> int:
    params = {
        "model": model,
        "model_version": model_version,
        "failure_limit": failure_limit,
    }
    async with connection.cursor() as cursor:
        await cursor.execute(COUNT_UNCOVERED_TARGETS_SQL, params)
        row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def delete_embeddings_except_models(
    connection: AsyncConnection, keep_models: list[tuple[str, str]]
) -> int:
    """An empty keep list deletes nothing, so a caller bug cannot wipe every vector."""
    if not keep_models:
        return 0
    params = {
        "models": [model for model, _ in keep_models],
        "model_versions": [model_version for _, model_version in keep_models],
    }
    async with connection.cursor() as cursor:
        await cursor.execute(DELETE_EMBEDDINGS_EXCEPT_MODELS_SQL, params)
        return cursor.rowcount


async def search_eligible_embeddings(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    model: str,
    model_version: str,
    query_vector: list[float],
    limit: int,
) -> list[VectorHit]:
    """Exact cosine scan over eligible span and fact embeddings of one model, nearest
    first. Only rows whose stored dimension equals `len(query_vector)` reach the
    distance operator, so models of other dimensions can coexist. Needs pgvector
    registered on the connection."""
    if not query_vector or limit <= 0:
        return []
    params = {
        **ctx.to_params(),
        "model": model,
        "model_version": model_version,
        "dim": len(query_vector),
        "query_vector": Vector(query_vector),
        "limit": limit,
    }
    async with connection.cursor(row_factory=class_row(VectorHit)) as cursor:
        await cursor.execute(SEARCH_ELIGIBLE_EMBEDDINGS_SQL, params)
        return await cursor.fetchall()


DELETE_SCOPE_EMBEDDINGS_SQL = (
    "DELETE FROM memory_embedding "
    "WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s"
)


async def delete_scope_embeddings(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> int:
    async with connection.cursor() as cursor:
        await cursor.execute(
            DELETE_SCOPE_EMBEDDINGS_SQL,
            {"scope_kind": scope_kind, "scope_id": scope_id},
        )
        return cursor.rowcount
