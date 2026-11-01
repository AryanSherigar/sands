"""The typed context handed to the extraction step: exact and graph branches only."""

from uuid import UUID

from app.config import Settings
from app.models.eligibility import EligibilityContext
from app.models.retrieve import ExtractionContext, MemoryItem, RetrievalBranch
from app.models.templates import PlaythroughRow
from app.repositories import entity_repo
from app.services.fusion import Candidate, fuse
from app.services.packing import (
    PackBudget,
    PackResult,
    build_ranked_items,
    pack_items,
)
from app.services.retrieval_branches import run_exact_branch
from app.services.retrieval_graph import run_graph_branch
from app.services.retrieval_hydration import load_render_context
from app.services.retrieval_types import CandidatePool, build_scopes
from psycopg import AsyncConnection


def _context_entity_ids(seed_ids: list[UUID], items: list[MemoryItem]) -> list[UUID]:
    referenced = [entity_id for item in items for entity_id in item.entity_ids]
    return list(dict.fromkeys([*seed_ids, *referenced]))


async def _resolve_seed_ids(
    connection: AsyncConnection,
    playthrough: PlaythroughRow,
    seed_entity_ids: list[UUID],
) -> list[UUID]:
    scopes = build_scopes(playthrough.playthrough_id, playthrough.template_id)
    requested = list(dict.fromkeys(seed_entity_ids))
    rows = await entity_repo.get_entities(connection, scopes, requested)
    known = {row.entity_id for row in rows}
    return [entity_id for entity_id in requested if entity_id in known]


async def _extraction_rankings(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    playthrough: PlaythroughRow,
    seed_ids: list[UUID],
    pool: CandidatePool,
    settings: Settings,
) -> dict[RetrievalBranch, list[Candidate]]:
    exact = await run_exact_branch(
        connection, ctx, seed_ids, pool, settings, should_include_spans=False
    )
    graph = await run_graph_branch(
        connection,
        ctx,
        seed_ids,
        player_entity_id=playthrough.player_entity_id,
        pool=pool,
        settings=settings,
        should_include_spans=False,
    )
    return {"exact": exact, "graph": graph}


def _extraction_budget(token_cap: int, settings: Settings) -> PackBudget:
    return PackBudget(
        budget_tokens=token_cap,
        chars_per_token=settings.span_chars_per_token,
        graph_and_exact_only_share=settings.graph_and_exact_only_budget_share,
        should_limit_graph_and_exact_only=False,
    )


def _to_extraction_context(
    seed_ids: list[UUID], packed: PackResult
) -> ExtractionContext:
    return ExtractionContext(
        lines=[item.text for item in packed.items],
        items=packed.items,
        entity_ids=_context_entity_ids(seed_ids, packed.items),
        token_count=packed.token_count,
        truncated=packed.is_truncated,
    )


async def build_extraction_context(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    playthrough: PlaythroughRow,
    seed_entity_ids: list[UUID],
    token_cap: int,
    settings: Settings,
) -> ExtractionContext:
    """Only facts and commitments: the extraction step reads the turns themselves, so
    spans are left out. Hidden authored facts are included because extraction must
    be able to link to them; the output never reaches a narrator."""
    seed_ids = await _resolve_seed_ids(connection, playthrough, seed_entity_ids)
    pool = CandidatePool()
    rankings = await _extraction_rankings(
        connection, ctx, playthrough, seed_ids, pool, settings
    )
    fused = fuse(
        rankings,
        rrf_k=settings.rrf_k,
        single_branch_rank_floor=settings.single_branch_rank_floor,
    )
    scopes = build_scopes(playthrough.playthrough_id, playthrough.template_id)
    render_context = await load_render_context(connection, ctx, scopes, fused, pool, {})
    items = build_ranked_items(fused, pool, render_context)
    packed = pack_items(items, seed_ids, _extraction_budget(token_cap, settings))
    return _to_extraction_context(seed_ids, packed)
