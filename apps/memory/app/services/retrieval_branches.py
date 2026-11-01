"""The exact and BM25 candidate branches."""

from uuid import UUID

import psycopg
import structlog
from app.config import Settings
from app.models.eligibility import EligibilityContext
from app.models.evidence import SpanRow
from app.models.facts import CommitmentRow, CommitmentStatusRow, FactRow
from app.repositories import commitment_repo, fact_repo, span_repo
from app.services.fusion import Candidate
from app.services.retrieval_types import CandidatePool, CommitmentRecord
from psycopg import AsyncConnection

logger = structlog.get_logger()


def order_by_recency(candidates: list[Candidate]) -> list[Candidate]:
    """Sequence descending, then id ascending: one total order for every merge."""
    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate.sequence,
            str(candidate.item_id),
            candidate.kind,
        ),
    )


def _register_candidates(
    pool: CandidatePool,
    facts: list[FactRow],
    commitments: list[tuple[CommitmentRow, CommitmentStatusRow | None]],
    spans: list[SpanRow],
) -> list[Candidate]:
    candidates = [pool.add_fact(fact) for fact in facts]
    candidates += [
        pool.add_commitment(CommitmentRecord(commitment, status))
        for commitment, status in commitments
    ]
    candidates += [pool.add_span(span) for span in spans]
    return candidates


async def run_exact_branch(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    seed_ids: list[UUID],
    pool: CandidatePool,
    settings: Settings,
    *,
    should_include_spans: bool = True,
) -> list[Candidate]:
    """Facts, commitments and (optionally) spans anchored on the seeds, queried per
    kind and merged newest first."""
    limit = settings.branch_candidate_cap
    facts = await fact_repo.list_eligible_facts_for_entities(
        connection, ctx, seed_ids, limit
    )
    commitments = await commitment_repo.list_eligible_commitments(
        connection,
        ctx,
        seed_ids,
        recent_resolution_turns=settings.commitment_recent_resolution_turns,
        limit=limit,
    )
    spans = []
    if should_include_spans:
        spans = await span_repo.list_exact_spans(connection, ctx, seed_ids, limit)
    candidates = _register_candidates(pool, facts, commitments, spans)
    return order_by_recency(candidates)[:limit]


async def run_bm25_branch(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    query_text: str,
    pool: CandidatePool,
    settings: Settings,
) -> list[Candidate] | None:
    """None means the branch failed and was skipped. The query runs in a savepoint,
    so a database error rolls back only this branch and the request's snapshot stays
    usable for the branches that follow."""
    try:
        async with connection.transaction():
            hits = await span_repo.search_eligible_spans_bm25(
                connection, ctx, query_text, settings.branch_candidate_cap
            )
    except psycopg.Error as error:
        logger.error(
            "retrieval_branch_failed",
            branch="bm25",
            playthrough_id=str(ctx.playthrough_id),
            at_seq=ctx.at_seq,
            error_class=type(error).__name__,
        )
        return None
    return [pool.add_span(span) for span, _score in hits]
