"""Embeds one batch of a claim and writes it or records its failure."""

import time

import structlog
from app.exceptions.indexing_exceptions import (
    EmbeddingAnomalyError,
    EmbeddingPermanentError,
    EmbeddingRateLimitedError,
    EmbeddingTransientError,
)
from app.models.jobs import EmbeddingCreate
from app.repositories import embedding_failure_repo, embedding_repo
from app.services.indexing_types import (
    ERROR_DIMENSION_MISMATCH,
    ERROR_FALLBACK,
    STEP_ABORTED,
    STEP_RATE_LIMITED,
    EmbedTarget,
    SweepContext,
    SweepState,
)
from app.services.ingest_common import sha256_hex
from psycopg import AsyncConnection

logger = structlog.get_logger()

OUTCOME_WRITTEN = "written"
OUTCOME_RATE_LIMITED = "rate_limited"
OUTCOME_TRANSIENT = "transient"
OUTCOME_PERMANENT = "permanent"
OUTCOME_ANOMALY = "anomaly"
OUTCOME_DIMENSION_MISMATCH = "dimension_mismatch"
MILLISECONDS_PER_SECOND = 1000
TARGET_KINDS = ("span", "fact")


async def embed_batch(
    ctx: SweepContext,
    state: SweepState,
    connection: AsyncConnection,
    batch: list[EmbedTarget],
) -> None:
    started = time.monotonic()
    state.batches_sent += 1
    outcome = await _attempt_batch(ctx, state, connection, batch)
    elapsed_ms = int((time.monotonic() - started) * MILLISECONDS_PER_SECOND)
    _log_batch(ctx, batch, outcome, elapsed_ms)


async def _attempt_batch(
    ctx: SweepContext,
    state: SweepState,
    connection: AsyncConnection,
    batch: list[EmbedTarget],
) -> str:
    try:
        vectors = await ctx.embedder.embed_documents(
            [target.body for target in batch], ctx.deadline_monotonic
        )
        if len(vectors) != len(batch):
            raise EmbeddingAnomalyError("Embedding count did not match input count.")
    except EmbeddingRateLimitedError as error:
        state.request_stop(STEP_RATE_LIMITED, error.code or ERROR_FALLBACK)
        return OUTCOME_RATE_LIMITED
    except EmbeddingTransientError as error:
        state.request_stop(STEP_RATE_LIMITED, error.code or ERROR_FALLBACK)
        return OUTCOME_TRANSIENT
    except (EmbeddingPermanentError, EmbeddingAnomalyError) as error:
        return await _reject_batch(ctx, state, connection, batch, error)
    await _write_batch(ctx, state, connection, batch, vectors)
    return OUTCOME_WRITTEN


async def _write_batch(
    ctx: SweepContext,
    state: SweepState,
    connection: AsyncConnection,
    batch: list[EmbedTarget],
    vectors: list[list[float]],
) -> None:
    embeddings = [
        EmbeddingCreate(
            target_kind=target.kind,
            target_id=target.target_id,
            scope_kind=target.scope_kind,
            scope_id=target.scope_id,
            model=ctx.model.model,
            model_version=ctx.model.model_version,
            dim=ctx.model.dim,
            embedding=vector,
            content_hash=sha256_hex(target.body),
        )
        for target, vector in zip(batch, vectors, strict=True)
    ]
    await embedding_repo.insert_embeddings(connection, embeddings)
    state.spans_embedded += sum(1 for target in batch if target.kind == "span")
    state.facts_embedded += sum(1 for target in batch if target.kind == "fact")
    state.chars_embedded += sum(len(target.body) for target in batch)


def _is_dimension_mismatch(error: Exception) -> bool:
    return isinstance(error, EmbeddingAnomalyError) and error.is_dimension_mismatch


async def _reject_batch(
    ctx: SweepContext,
    state: SweepState,
    connection: AsyncConnection,
    batch: list[EmbedTarget],
    error: EmbeddingPermanentError | EmbeddingAnomalyError,
) -> str:
    if _is_dimension_mismatch(error):
        await _abort_on_dimension_mismatch(ctx, state, connection, batch)
        return OUTCOME_DIMENSION_MISMATCH
    error_code = error.code or ERROR_FALLBACK
    await _record_batch_failures(ctx, state, connection, batch, error_code)
    state.add_error(error_code)
    if isinstance(error, EmbeddingAnomalyError):
        return OUTCOME_ANOMALY
    return OUTCOME_PERMANENT


async def _abort_on_dimension_mismatch(
    ctx: SweepContext,
    state: SweepState,
    connection: AsyncConnection,
    batch: list[EmbedTarget],
) -> None:
    await _record_batch_failures(
        ctx, state, connection, batch, ERROR_DIMENSION_MISMATCH
    )
    logger.error(
        "embedding_dimension_mismatch",
        model=ctx.model.model,
        model_version=ctx.model.model_version,
        configured_dim=ctx.model.dim,
        batch_size=len(batch),
    )
    state.request_stop(STEP_ABORTED, ERROR_DIMENSION_MISMATCH)


async def _record_batch_failures(
    ctx: SweepContext,
    state: SweepState,
    connection: AsyncConnection,
    batch: list[EmbedTarget],
    error_code: str,
) -> None:
    for kind in TARGET_KINDS:
        target_ids = [target.target_id for target in batch if target.kind == kind]
        rows = await embedding_failure_repo.record_failures(
            connection,
            kind,
            target_ids,
            ctx.model.model,
            ctx.model.model_version,
            error_code,
        )
        state.failed_ids(kind).update(target_ids)
        skipped = [
            str(row.target_id)
            for row in rows
            if row.attempt_count >= ctx.settings.embedding_failure_limit
        ]
        _log_skipped(state, kind, skipped, error_code)


def _log_skipped(
    state: SweepState, kind: str, skipped_ids: list[str], error_code: str
) -> None:
    if not skipped_ids:
        return
    state.targets_skipped += len(skipped_ids)
    logger.warning(
        "embedding_targets_skipped",
        target_kind=kind,
        target_ids=skipped_ids,
        error_code=error_code,
    )


def _log_batch(
    ctx: SweepContext, batch: list[EmbedTarget], outcome: str, elapsed_ms: int
) -> None:
    log = logger.info if outcome == OUTCOME_WRITTEN else logger.warning
    log(
        "embedding_batch",
        model=ctx.model.model,
        model_version=ctx.model.model_version,
        batch_size=len(batch),
        span_count=sum(1 for target in batch if target.kind == "span"),
        fact_count=sum(1 for target in batch if target.kind == "fact"),
        chars=sum(len(target.body) for target in batch),
        elapsed_ms=elapsed_ms,
        outcome=outcome,
    )
