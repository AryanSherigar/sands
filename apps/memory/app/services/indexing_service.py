"""Orchestrates one process-pending sweep: reconcile, embed, advance, flip."""

import time
from functools import lru_cache

import structlog
from app.config import Settings, get_settings
from app.db.pool import get_pool
from app.integrations.embedding_client import EmbeddingClient, build_embedding_client
from app.models.process_pending import (
    EmbeddingStepStatus,
    ProcessPendingCounts,
    ProcessPendingRequest,
    ProcessPendingResponse,
)
from app.services.extraction_service import (
    ExtractionService,
    get_extraction_service,
)
from app.services.indexing_model import (
    ModelReconciliation,
    delete_stale_vectors,
    flip_model_if_covered,
    reconcile_embedding_model,
)
from app.services.indexing_types import DocumentEmbedder, SweepContext, SweepState
from app.services.indexing_watermark import advance_index_watermarks
from app.services.indexing_worker import has_remaining_work, run_workers
from app.services.purge_service import PurgeService
from app.services.template_gc import collect_template_garbage
from psycopg import Error as DatabaseError
from psycopg_pool import AsyncConnectionPool

logger = structlog.get_logger()

EVENT_TEMPLATE_GC_FAILED = "template_gc_failed"

__all__ = ["DocumentEmbedder", "IndexingService", "get_indexing_service"]


class IndexingService:
    def __init__(
        self,
        pool: AsyncConnectionPool,
        settings: Settings,
        embedder: DocumentEmbedder | None,
        extraction: ExtractionService | None = None,
    ) -> None:
        self._pool = pool
        self._settings = settings
        self._embedder = embedder
        self._extraction = extraction

    async def process_pending(
        self, request: ProcessPendingRequest | None = None
    ) -> ProcessPendingResponse:
        """Never raises for provider failures; they are reported in the body. Embedding
        runs first within a capped share of the deadline so extraction keeps a floor."""
        request = request or ProcessPendingRequest()
        total_seconds = (
            request.deadline_seconds or self._settings.process_pending_deadline_seconds
        )
        deadline_monotonic = time.monotonic() + total_seconds
        embedding_seconds = self._embedding_seconds(total_seconds)
        embedding = await self._embedding_step(request, embedding_seconds)
        result = await self._with_extraction(embedding, request, deadline_monotonic)
        if request.playthrough_id is not None:
            return result
        return await self._with_template_gc(result)

    async def _with_template_gc(
        self, response: ProcessPendingResponse
    ) -> ProcessPendingResponse:
        try:
            gc_result = await collect_template_garbage(
                self._pool,
                PurgeService(self._pool),
                self._settings.template_gc_failed_age_seconds,
            )
        except DatabaseError:
            logger.exception(EVENT_TEMPLATE_GC_FAILED)
            return response.model_copy(
                update={"errors": [*response.errors, EVENT_TEMPLATE_GC_FAILED]}
            )
        counts = response.counts.model_copy(
            update={
                "templates_gc_deleted": gc_result.deleted,
                "templates_gc_retained": gc_result.retained,
            }
        )
        return response.model_copy(update={"counts": counts})

    def _embedding_seconds(self, total_seconds: float) -> float:
        if self._extraction is None or not self._extraction.is_configured:
            return total_seconds
        return total_seconds * self._settings.embedding_deadline_share

    async def _embedding_step(
        self, request: ProcessPendingRequest, deadline_seconds: float
    ) -> ProcessPendingResponse:
        if self._embedder is None:
            logger.warning("embedding_unconfigured")
            return ProcessPendingResponse(
                embedding_step="unconfigured", counts=ProcessPendingCounts()
            )
        return await self._sweep(self._embedder, request, deadline_seconds)

    async def _with_extraction(
        self,
        embedding: ProcessPendingResponse,
        request: ProcessPendingRequest,
        deadline_monotonic: float,
    ) -> ProcessPendingResponse:
        if self._extraction is None:
            return embedding
        result = await self._extraction.process(
            request.playthrough_id, deadline_monotonic
        )
        return embedding.model_copy(
            update={
                "extraction_step": result.step,
                "extraction_counts": result.counts,
                "errors": [*embedding.errors, *result.errors],
            }
        )

    async def _sweep(
        self,
        embedder: DocumentEmbedder,
        request: ProcessPendingRequest,
        deadline_seconds: float,
    ) -> ProcessPendingResponse:
        reconciliation = await reconcile_embedding_model(self._pool, self._settings)
        ctx = SweepContext(
            pool=self._pool,
            settings=self._settings,
            embedder=embedder,
            model=reconciliation.configured,
            playthrough_id=request.playthrough_id,
            deadline_monotonic=time.monotonic() + deadline_seconds,
        )
        deleted = 0
        if ctx.is_unscoped:
            deleted = await delete_stale_vectors(self._pool, reconciliation)
        state = SweepState()
        await run_workers(ctx, state)
        return await self._finish_sweep(ctx, state, reconciliation, deleted)

    async def _finish_sweep(
        self,
        ctx: SweepContext,
        state: SweepState,
        reconciliation: ModelReconciliation,
        deleted: int,
    ) -> ProcessPendingResponse:
        advanced = await advance_index_watermarks(
            self._pool,
            ctx.model,
            self._settings.embedding_failure_limit,
            ctx.playthrough_id,
        )
        is_flipped = False
        if ctx.is_unscoped and not state.is_stopped:
            is_flipped = await flip_model_if_covered(
                self._pool, self._settings, reconciliation
            )
        counts = _build_counts(state, self._settings)
        counts.playthroughs_advanced = advanced
        counts.model_flipped = is_flipped
        counts.old_vectors_deleted = deleted
        step = await _resolve_step(ctx, state)
        return ProcessPendingResponse(
            embedding_step=step, counts=counts, errors=list(state.errors)
        )


async def _resolve_step(ctx: SweepContext, state: SweepState) -> EmbeddingStepStatus:
    if state.stop_step is not None:
        return state.stop_step
    if state.is_cut_by_deadline and await has_remaining_work(ctx):
        return "deadline_reached"
    if state.targets_claimed == 0:
        return "idle"
    return "completed"


def _build_counts(state: SweepState, settings: Settings) -> ProcessPendingCounts:
    return ProcessPendingCounts(
        spans_embedded=state.spans_embedded,
        facts_embedded=state.facts_embedded,
        characters_embedded=state.chars_embedded,
        tokens_estimated=state.chars_embedded // settings.span_chars_per_token,
        batches_sent=state.batches_sent,
        targets_skipped=state.targets_skipped,
    )


@lru_cache
def _get_embedding_client() -> EmbeddingClient | None:
    return build_embedding_client(get_settings())


def get_indexing_service() -> IndexingService:
    return IndexingService(
        get_pool(),
        get_settings(),
        _get_embedding_client(),
        get_extraction_service(),
    )
