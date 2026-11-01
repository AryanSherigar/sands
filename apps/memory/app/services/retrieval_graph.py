"""The graph candidate branch: one or two hops of eligible relation facts."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.config import Settings
from app.models.eligibility import EligibilityContext
from app.models.facts import FactRow
from app.models.retrieval_rows import GraphEdges
from app.repositories import commitment_repo, fact_repo
from app.services.fusion import Candidate, CandidateKey
from app.services.retrieval_types import CandidatePool, CommitmentRecord
from psycopg import AsyncConnection

FIRST_HOP = 1
SECOND_HOP = 2


@dataclass(frozen=True)
class Traversal:
    hop_by_edge_id: dict[UUID, int]
    edges: list[FactRow]
    hub_entity_ids: frozenset[UUID]


def _far_end_ids(
    edges: list[FactRow], excluded: set[UUID] | frozenset[UUID]
) -> list[UUID]:
    found: list[UUID] = []
    for edge in edges:
        found.extend([edge.subject_entity_id, edge.object_entity_id])
    return list(
        dict.fromkeys(
            entity_id
            for entity_id in found
            if entity_id is not None and entity_id not in excluded
        )
    )


async def _list_edges(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    frontier: list[UUID],
    player_entity_id: UUID | None,
    settings: Settings,
    *,
    should_expand_hubs: bool,
) -> GraphEdges:
    return await fact_repo.list_graph_edges(
        connection,
        ctx,
        frontier,
        hub_edge_cap=settings.hub_edge_cap,
        player_entity_id=player_entity_id,
        should_expand_hubs=should_expand_hubs,
    )


async def traverse(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    seed_ids: list[UUID],
    player_entity_id: UUID | None,
    settings: Settings,
) -> Traversal:
    """Hop 1 from the seeds. The second query always runs so hubs among the
    neighbours are known (a hub never expands), but its edges are kept only when hop
    1 found fewer than `graph_hop2_min` edges."""
    hop_one = await _list_edges(
        connection, ctx, seed_ids, player_entity_id, settings, should_expand_hubs=True
    )
    frontier = _far_end_ids(hop_one.edges, set(seed_ids) | hop_one.hub_entity_ids)
    probe = await _list_edges(
        connection, ctx, frontier, player_entity_id, settings, should_expand_hubs=False
    )
    hop_two: list[FactRow] = []
    if len(hop_one.edges) < settings.graph_hop2_min:
        first_hop_ids = {edge.fact_id for edge in hop_one.edges}
        hop_two = [e for e in probe.edges if e.fact_id not in first_hop_ids]
    hops = {edge.fact_id: FIRST_HOP for edge in hop_one.edges}
    hops.update({edge.fact_id: SECOND_HOP for edge in hop_two})
    hubs = hop_one.hub_entity_ids | probe.hub_entity_ids
    if player_entity_id is not None:
        hubs = hubs | {player_entity_id}
    return Traversal(hops, [*hop_one.edges, *hop_two], hubs)


def _neighbour_hops(traversal: Traversal, seed_ids: list[UUID]) -> dict[UUID, int]:
    """Each neighbour's nearest hop. Seeds and hubs never count as neighbours."""
    excluded = set(seed_ids) | traversal.hub_entity_ids
    hops: dict[UUID, int] = {}
    for edge in traversal.edges:
        hop = traversal.hop_by_edge_id[edge.fact_id]
        for entity_id in _far_end_ids([edge], excluded):
            hops[entity_id] = min(hop, hops.get(entity_id, hop))
    return hops


def _nearest_hop(entity_ids: Sequence[UUID | None], hops: dict[UUID, int]) -> int:
    known = [hops[entity_id] for entity_id in entity_ids if entity_id in hops]
    return min(known, default=SECOND_HOP)


async def _neighbour_fact_entries(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    neighbour_hops: dict[UUID, int],
    pool: CandidatePool,
    settings: Settings,
) -> list[tuple[int, Candidate]]:
    facts = await fact_repo.list_eligible_literal_facts_for_entities(
        connection, ctx, list(neighbour_hops), settings.branch_candidate_cap
    )
    return [
        (
            _nearest_hop(
                [fact.subject_entity_id, fact.object_entity_id], neighbour_hops
            ),
            pool.add_fact(fact),
        )
        for fact in facts
    ]


async def _neighbour_commitment_entries(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    neighbour_hops: dict[UUID, int],
    pool: CandidatePool,
    settings: Settings,
) -> list[tuple[int, Candidate]]:
    rows = await commitment_repo.list_eligible_commitments(
        connection,
        ctx,
        list(neighbour_hops),
        recent_resolution_turns=settings.commitment_recent_resolution_turns,
        limit=settings.branch_candidate_cap,
    )
    records = [CommitmentRecord(commitment, status) for commitment, status in rows]
    return [
        (
            _nearest_hop(
                [
                    record.commitment.owner_entity_id,
                    record.commitment.counterparty_entity_id,
                ],
                neighbour_hops,
            ),
            pool.add_commitment(record),
        )
        for record in records
        if record.is_open
    ]


async def _edge_span_candidates(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    traversal: Traversal,
    pool: CandidatePool,
) -> list[tuple[int, Candidate]]:
    spans = await fact_repo.get_representative_source_spans(
        connection, ctx, [edge.fact_id for edge in traversal.edges]
    )
    return [
        (traversal.hop_by_edge_id[fact_id], pool.add_span(span))
        for fact_id, span in spans.items()
    ]


def _rank_by_hop_then_recency(
    entries: list[tuple[int, Candidate]], limit: int
) -> list[Candidate]:
    nearest: dict[CandidateKey, tuple[int, Candidate]] = {}
    for hop, candidate in entries:
        current = nearest.get(candidate.key)
        if current is None or hop < current[0]:
            nearest[candidate.key] = (hop, candidate)
    ranked = sorted(
        nearest.values(),
        key=lambda entry: (
            entry[0],
            -entry[1].sequence,
            str(entry[1].item_id),
            entry[1].kind,
        ),
    )
    return [candidate for _hop, candidate in ranked][:limit]


async def run_graph_branch(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    seed_ids: list[UUID],
    *,
    player_entity_id: UUID | None,
    pool: CandidatePool,
    settings: Settings,
    should_include_spans: bool = True,
) -> list[Candidate]:
    """Edge facts, the neighbours' current facts and open commitments, and one
    eligible source span per edge; ranked by hop, then newest first."""
    traversal = await traverse(connection, ctx, seed_ids, player_entity_id, settings)
    entries = [
        (traversal.hop_by_edge_id[edge.fact_id], pool.add_fact(edge))
        for edge in traversal.edges
    ]
    neighbour_hops = _neighbour_hops(traversal, seed_ids)
    if neighbour_hops:
        args = (connection, ctx, neighbour_hops, pool, settings)
        entries += await _neighbour_fact_entries(*args)
        entries += await _neighbour_commitment_entries(*args)
    if should_include_spans:
        entries += await _edge_span_candidates(connection, ctx, traversal, pool)
    return _rank_by_hop_then_recency(entries, settings.branch_candidate_cap)
