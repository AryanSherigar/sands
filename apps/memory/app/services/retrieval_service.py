"""Eligibility-first hybrid recall for one turn, and the extraction context."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from uuid import UUID

from app.config import Settings, get_settings
from app.db.pool import get_pool
from app.exceptions.ingest_exceptions import PlaythroughNotRegisteredError
from app.integrations.embedding_client import build_embedding_client
from app.models.retrieve import ExtractionContext, RetrieveRequest, RetrieveResponse
from app.models.templates import PlaythroughRow
from app.repositories import (
    embedding_repo,
    playthrough_repo,
    scene_repo,
    snapshot_repo,
)
from app.services.degraded_service import compute_degraded_reasons
from app.services.eligibility import build_eligibility_context
from app.services.fusion import fuse
from app.services.packing import (
    PackBudget,
    PackResult,
    build_ranked_items,
    pack_items,
)
from app.services.retrieval_branches import run_bm25_branch, run_exact_branch
from app.services.retrieval_extraction import build_extraction_context
from app.services.retrieval_graph import run_graph_branch
from app.services.retrieval_hydration import load_render_context
from app.services.retrieval_plan import RetrievalPlan, build_plan
from app.services.retrieval_response import assemble_response, log_retrieval
from app.services.retrieval_types import RetrievalRun
from app.services.retrieval_vector import (
    EmbedTask,
    QueryEmbedder,
    cancel_query_embedding,
    run_vector_branch,
    start_query_embedding,
)
from app.services.seeding import SeedRequest, resolve_seeds
from pgvector.psycopg import register_vector_async
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

__all__ = ["QueryEmbedder", "RetrievalService", "get_retrieval_service"]

EXTRACTION_RECENT_WINDOW_TURNS = 0


class RetrievalService:
    def __init__(
        self,
        pool: AsyncConnectionPool,
        settings: Settings,
        query_embedder: QueryEmbedder | None,
    ) -> None:
        self._pool = pool
        self._settings = settings
        self._query_embedder = query_embedder

    @asynccontextmanager
    async def _read_snapshot(self) -> AsyncIterator[AsyncConnection]:
        async with self._pool.connection() as connection, connection.transaction():
            await snapshot_repo.begin_read_only_snapshot(connection)
            await register_vector_async(connection)
            yield connection

    async def _require_playthrough(
        self, connection: AsyncConnection, playthrough_id: UUID
    ) -> PlaythroughRow:
        playthrough = await playthrough_repo.get_playthrough(connection, playthrough_id)
        if playthrough is None:
            raise PlaythroughNotRegisteredError(playthrough_id)
        return playthrough

    async def retrieve(self, request: RetrieveRequest) -> RetrieveResponse:
        """Never raises for an embedding or BM25 failure; those branches are reported
        in `skipped_branches`. Raises PlaythroughNotRegisteredError for an unknown
        playthrough."""
        async with self._read_snapshot() as connection:
            playthrough = await self._require_playthrough(
                connection, request.playthrough_id
            )
            plan = build_plan(request, playthrough, self._settings)
            run = RetrievalRun()
            embed_task = await start_query_embedding(
                self._query_embedder,
                plan.query_text,
                self._settings.retrieval_embed_timeout_seconds,
            )
            try:
                await self._gather_candidates(
                    connection, request, playthrough, plan, embed_task, run
                )
            finally:
                await cancel_query_embedding(embed_task)
            return await self._finish(connection, request, playthrough, plan, run)

    async def _gather_candidates(
        self,
        connection: AsyncConnection,
        request: RetrieveRequest,
        playthrough: PlaythroughRow,
        plan: RetrievalPlan,
        embed_task: EmbedTask | None,
        run: RetrievalRun,
    ) -> None:
        run.active_model = await embedding_repo.get_active_embedding_model(connection)
        await self._run_lookup_branches(connection, request, playthrough, plan, run)
        with run.timer.measure("vector"):
            await self._run_vector(connection, plan, embed_task, run)

    async def _run_lookup_branches(
        self,
        connection: AsyncConnection,
        request: RetrieveRequest,
        playthrough: PlaythroughRow,
        plan: RetrievalPlan,
        run: RetrievalRun,
    ) -> None:
        settings = self._settings
        with run.timer.measure("seeds"):
            await self._resolve_run_seeds(connection, request, playthrough, run)
        with run.timer.measure("exact"):
            run.rankings["exact"] = await run_exact_branch(
                connection, plan.ctx, run.seed_ids, run.pool, settings
            )
        with run.timer.measure("bm25"):
            await self._run_bm25(connection, plan, run)
        with run.timer.measure("graph"):
            run.rankings["graph"] = await run_graph_branch(
                connection,
                plan.ctx,
                run.seed_ids,
                player_entity_id=playthrough.player_entity_id,
                pool=run.pool,
                settings=settings,
            )

    async def _resolve_run_seeds(
        self,
        connection: AsyncConnection,
        request: RetrieveRequest,
        playthrough: PlaythroughRow,
        run: RetrievalRun,
    ) -> None:
        run.scene = await scene_repo.get_scene_at(
            connection, request.playthrough_id, request.sequence
        )
        run.seeds = await resolve_seeds(
            connection, self._build_seed_request(request, playthrough, run)
        )

    def _build_seed_request(
        self, request: RetrieveRequest, playthrough: PlaythroughRow, run: RetrievalRun
    ) -> SeedRequest:
        return SeedRequest(
            playthrough_id=playthrough.playthrough_id,
            template_id=playthrough.template_id,
            action_text=request.action_text,
            recent_text=request.recent_text,
            scene_authored_entity_ids=request.scene_authored_entity_ids,
            interlocutor_authored_entity_id=request.interlocutor_authored_entity_id,
            scene=run.scene,
            seed_cap=self._settings.seed_cap,
            ambiguous_alias_seed_cap=self._settings.ambiguous_alias_seed_cap,
        )

    async def _run_bm25(
        self, connection: AsyncConnection, plan: RetrievalPlan, run: RetrievalRun
    ) -> None:
        if not plan.query_text:
            return
        ranking = await run_bm25_branch(
            connection, plan.ctx, plan.query_text, run.pool, self._settings
        )
        if ranking is None:
            run.skipped.append("bm25")
        else:
            run.rankings["bm25"] = ranking

    async def _run_vector(
        self,
        connection: AsyncConnection,
        plan: RetrievalPlan,
        embed_task: EmbedTask | None,
        run: RetrievalRun,
    ) -> None:
        if not plan.query_text:
            return
        ranking = await run_vector_branch(
            connection,
            plan.ctx,
            embed_task=embed_task,
            active_model=run.active_model,
            pool=run.pool,
            settings=self._settings,
        )
        if ranking is None:
            run.skipped.append("vector")
        else:
            run.rankings["vector"] = ranking

    async def _pack(
        self,
        connection: AsyncConnection,
        request: RetrieveRequest,
        plan: RetrievalPlan,
        run: RetrievalRun,
    ) -> PackResult:
        settings = self._settings
        fused = fuse(
            run.rankings,
            rrf_k=settings.rrf_k,
            single_branch_rank_floor=settings.single_branch_rank_floor,
        )
        render_context = await load_render_context(
            connection,
            plan.ctx,
            plan.scopes,
            fused,
            run.pool,
            request.participant_names,
        )
        budget = PackBudget(
            budget_tokens=plan.budget_tokens,
            chars_per_token=settings.span_chars_per_token,
            graph_and_exact_only_share=settings.graph_and_exact_only_budget_share,
        )
        ranked = build_ranked_items(fused, run.pool, render_context)
        return pack_items(ranked, run.seed_ids, budget)

    async def _finish(
        self,
        connection: AsyncConnection,
        request: RetrieveRequest,
        playthrough: PlaythroughRow,
        plan: RetrievalPlan,
        run: RetrievalRun,
    ) -> RetrieveResponse:
        with run.timer.measure("pack"):
            packed = await self._pack(connection, request, plan, run)
        degraded = await compute_degraded_reasons(
            connection, playthrough, recent_window_turns=plan.recent_window_turns
        )
        response = assemble_response(
            items=packed.items,
            run=run,
            playthrough=playthrough,
            degraded_reasons=degraded,
        )
        log_retrieval(request, run, response, packed.token_count)
        return response

    async def extraction_context(
        self,
        playthrough_id: UUID,
        seed_entity_ids: list[UUID],
        at_seq: int,
        token_cap: int | None = None,
    ) -> ExtractionContext:
        """Internal, no route. Facts and commitments from the exact and graph branches
        at `at_seq`, hidden authored facts included."""
        async with self._read_snapshot() as connection:
            playthrough = await self._require_playthrough(connection, playthrough_id)
            ctx = build_eligibility_context(
                playthrough_id=playthrough_id,
                template_id=playthrough.template_id,
                at_seq=at_seq,
                recent_window_turns=EXTRACTION_RECENT_WINDOW_TURNS,
                revealed_fact_ids=[],
                active_conditional_fact_ids=[],
                should_include_hidden=True,
            )
            return await build_extraction_context(
                connection,
                ctx,
                playthrough,
                seed_entity_ids,
                token_cap or self._settings.extraction_context_tokens,
                self._settings,
            )


@lru_cache
def _get_query_embedder() -> QueryEmbedder | None:
    client = build_embedding_client(get_settings())
    return client.embed_query if client is not None else None


def get_retrieval_service() -> RetrievalService:
    return RetrievalService(get_pool(), get_settings(), _get_query_embedder())
