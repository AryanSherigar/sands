"""The vector candidate branch and the concurrent query-embedding task it consumes."""

import asyncio
from collections.abc import Awaitable, Callable

import psycopg
import structlog
from app.config import Settings
from app.exceptions.base import MemoryServiceError
from app.models.eligibility import EligibilityContext
from app.models.jobs import EmbeddingModelRow
from app.models.retrieval_rows import VectorHit
from app.repositories import embedding_repo, fact_repo, span_repo
from app.services.fusion import Candidate
from app.services.retrieval_types import CandidatePool
from psycopg import AsyncConnection

logger = structlog.get_logger()

QueryEmbedder = Callable[[str], Awaitable[list[float]]]
EmbedTask = asyncio.Task[list[float]]


async def start_query_embedding(
    embedder: QueryEmbedder | None, query_text: str, timeout_seconds: float
) -> EmbedTask | None:
    """Starts the embedding now, so it overlaps the database branches. Yields once so
    the task has begun before the caller's first database call."""
    if embedder is None or not query_text:
        return None
    task = asyncio.create_task(
        asyncio.wait_for(embedder(query_text), timeout=timeout_seconds)
    )
    await asyncio.sleep(0)
    return task


async def cancel_query_embedding(task: EmbedTask | None) -> None:
    if task is None:
        return
    if task.done():
        if not task.cancelled():
            task.exception()
        return
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def _await_query_vector(task: EmbedTask) -> list[float] | None:
    try:
        return await task
    except (MemoryServiceError, TimeoutError) as error:
        logger.warning("retrieval_embed_failed", error_class=type(error).__name__)
        return None


def is_active_model_configured(
    active_model: EmbeddingModelRow | None, settings: Settings
) -> bool:
    return (
        active_model is not None
        and active_model.model == settings.embedding_model_name
        and active_model.model_version == settings.embedding_model_version
    )


async def _hydrate_hits(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    hits: list[VectorHit],
    pool: CandidatePool,
) -> list[Candidate]:
    span_ids = [hit.target_id for hit in hits if hit.target_kind == "span"]
    fact_ids = [hit.target_id for hit in hits if hit.target_kind == "fact"]
    spans = await span_repo.get_eligible_spans_by_ids(connection, ctx, span_ids)
    facts = await fact_repo.get_eligible_facts_by_ids(connection, ctx, fact_ids)
    by_key = {("span", span.span_id): pool.add_span(span) for span in spans}
    by_key.update({("fact", fact.fact_id): pool.add_fact(fact) for fact in facts})
    ordered = [by_key.get((hit.target_kind, hit.target_id)) for hit in hits]
    return [candidate for candidate in ordered if candidate is not None]


async def _search(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    query_vector: list[float],
    pool: CandidatePool,
    settings: Settings,
) -> list[Candidate] | None:
    try:
        async with connection.transaction():
            hits = await embedding_repo.search_eligible_embeddings(
                connection,
                ctx,
                settings.embedding_model_name,
                settings.embedding_model_version,
                query_vector,
                settings.branch_candidate_cap,
            )
            return await _hydrate_hits(connection, ctx, hits, pool)
    except psycopg.Error as error:
        logger.error(
            "retrieval_branch_failed",
            branch="vector",
            playthrough_id=str(ctx.playthrough_id),
            at_seq=ctx.at_seq,
            error_class=type(error).__name__,
        )
        return None


async def run_vector_branch(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    *,
    embed_task: EmbedTask | None,
    active_model: EmbeddingModelRow | None,
    pool: CandidatePool,
    settings: Settings,
) -> list[Candidate] | None:
    """None means the branch was skipped: no embedder, an embed failure or timeout,
    the configured model is not the active one, or the search failed. Every skip
    leaves the other branches intact."""
    if not is_active_model_configured(active_model, settings):
        await cancel_query_embedding(embed_task)
        return None
    if embed_task is None:
        return None
    query_vector = await _await_query_vector(embed_task)
    if not query_vector:
        return None
    return await _search(connection, ctx, query_vector, pool, settings)
