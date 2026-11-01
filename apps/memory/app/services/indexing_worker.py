"""Claim-embed-commit workers of one sweep."""

import asyncio

from app.models.jobs import FactClaimRow, SpanClaimRow
from app.repositories import embedding_repo
from app.services.fact_text import render_fact_text
from app.services.indexing_batch import embed_batch
from app.services.indexing_types import EmbedTarget, SweepContext, SweepState
from pgvector.psycopg import register_vector_async
from psycopg import AsyncConnection


def chunked(targets: list[EmbedTarget], size: int) -> list[list[EmbedTarget]]:
    return [targets[start : start + size] for start in range(0, len(targets), size)]


def _span_target(row: SpanClaimRow) -> EmbedTarget:
    return EmbedTarget("span", row.span_id, row.scope_kind, row.scope_id, row.text)


def _fact_target(row: FactClaimRow) -> EmbedTarget:
    body = render_fact_text(row.subject_name, row.predicate, row.object_text or "")
    return EmbedTarget("fact", row.fact_id, row.scope_kind, row.scope_id, body)


async def _claim_spans(
    ctx: SweepContext, state: SweepState, connection: AsyncConnection, capacity: int
) -> list[EmbedTarget]:
    rows = await embedding_repo.claim_unembedded_spans(
        connection,
        ctx.model.model,
        ctx.model.model_version,
        capacity + len(state.failed_span_ids),
        ctx.settings.embedding_failure_limit,
        ctx.playthrough_id,
    )
    targets = [_span_target(row) for row in rows]
    fresh = [t for t in targets if t.target_id not in state.failed_span_ids]
    return fresh[:capacity]


async def _claim_facts(
    ctx: SweepContext, state: SweepState, connection: AsyncConnection, capacity: int
) -> list[EmbedTarget]:
    rows = await embedding_repo.claim_unembedded_facts(
        connection,
        ctx.model.model,
        ctx.model.model_version,
        capacity + len(state.failed_fact_ids),
        ctx.settings.embedding_failure_limit,
        ctx.playthrough_id,
    )
    targets = [_fact_target(row) for row in rows]
    fresh = [t for t in targets if t.target_id not in state.failed_fact_ids]
    return fresh[:capacity]


async def claim_targets(
    ctx: SweepContext, state: SweepState, connection: AsyncConnection
) -> list[EmbedTarget]:
    """Spans first, then facts with the remaining capacity.

    NOTE: the SQL limit is raised by the number of ids that already failed this
    sweep, so the window always holds claim-size fresh rows and a poison target is
    tried once per sweep instead of once per loop.
    """
    size = ctx.settings.embedding_claim_size
    spans = await _claim_spans(ctx, state, connection, size)
    if len(spans) >= size:
        return spans
    facts = await _claim_facts(ctx, state, connection, size - len(spans))
    return spans + facts


async def _embed_claim(
    ctx: SweepContext,
    state: SweepState,
    connection: AsyncConnection,
    targets: list[EmbedTarget],
) -> None:
    for batch in chunked(targets, ctx.settings.embedding_batch_size):
        if state.is_stopped:
            return
        if ctx.is_deadline_passed:
            state.is_cut_by_deadline = True
            return
        await embed_batch(ctx, state, connection, batch)


async def _process_one_claim(ctx: SweepContext, state: SweepState) -> int:
    async with ctx.pool.connection() as connection:
        await register_vector_async(connection)
        targets = await claim_targets(ctx, state, connection)
        state.targets_claimed += len(targets)
        await _embed_claim(ctx, state, connection, targets)
    return len(targets)


async def _run_worker(ctx: SweepContext, state: SweepState) -> None:
    while not state.is_stopped:
        if ctx.is_deadline_passed:
            state.is_cut_by_deadline = True
            return
        if await _process_one_claim(ctx, state) == 0:
            return


async def run_workers(ctx: SweepContext, state: SweepState) -> None:
    workers = [
        _run_worker(ctx, state) for _ in range(ctx.settings.embedding_concurrency)
    ]
    results = await asyncio.gather(*workers, return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException):
            raise result


async def has_remaining_work(ctx: SweepContext) -> bool:
    """A SKIP LOCKED probe, so rows another sweep is already embedding do not count."""
    async with ctx.pool.connection() as connection:
        args = (
            ctx.model.model,
            ctx.model.model_version,
            1,
            ctx.settings.embedding_failure_limit,
            ctx.playthrough_id,
        )
        spans = await embedding_repo.claim_unembedded_spans(connection, *args)
        facts = await embedding_repo.claim_unembedded_facts(connection, *args)
    return bool(spans or facts)
