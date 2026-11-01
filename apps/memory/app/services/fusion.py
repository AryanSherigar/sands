"""Reciprocal Rank Fusion, the single-branch relevance gate and the final order. Pure."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal
from uuid import UUID

from app.models.retrieve import RetrievalBranch

CandidateKind = Literal["span", "fact", "commitment"]
CandidateKey = tuple[CandidateKind, UUID]

BRANCH_ORDER: tuple[RetrievalBranch, ...] = ("exact", "bm25", "vector", "graph")
GATED_BRANCHES: frozenset[RetrievalBranch] = frozenset({"bm25", "vector"})
FIRST_RANK = 1


@dataclass(frozen=True)
class Candidate:
    kind: CandidateKind
    item_id: UUID
    sequence: int

    @property
    def key(self) -> CandidateKey:
        return (self.kind, self.item_id)


@dataclass(frozen=True)
class FusedCandidate:
    """`ranks` maps each branch that returned the candidate to its 1-based rank there,
    in `BRANCH_ORDER`. `score` is exact so equal scores tie for real."""

    candidate: Candidate
    score: Fraction
    ranks: Mapping[RetrievalBranch, int]

    @property
    def branches(self) -> list[RetrievalBranch]:
        return list(self.ranks)


def _distinct(entries: Iterable[Candidate]) -> list[Candidate]:
    first_by_key: dict[CandidateKey, Candidate] = {}
    for entry in entries:
        first_by_key.setdefault(entry.key, entry)
    return list(first_by_key.values())


def _rrf_score(ranks: Mapping[RetrievalBranch, int], rrf_k: int) -> Fraction:
    return sum((Fraction(1, rrf_k + rank) for rank in ranks.values()), Fraction(0))


def _collect_ranks(
    rankings: Mapping[RetrievalBranch, Sequence[Candidate]],
) -> tuple[
    dict[CandidateKey, Candidate], dict[CandidateKey, dict[RetrievalBranch, int]]
]:
    candidates: dict[CandidateKey, Candidate] = {}
    ranks_by_key: dict[CandidateKey, dict[RetrievalBranch, int]] = {}
    for branch in BRANCH_ORDER:
        ranked = _distinct(rankings.get(branch, ()))
        for rank, candidate in enumerate(ranked, start=FIRST_RANK):
            candidates.setdefault(candidate.key, candidate)
            ranks_by_key.setdefault(candidate.key, {})[branch] = rank
    return candidates, ranks_by_key


def _is_gated_out(fused: FusedCandidate, single_branch_rank_floor: int) -> bool:
    if len(fused.ranks) != 1:
        return False
    ((branch, rank),) = fused.ranks.items()
    return branch in GATED_BRANCHES and rank > single_branch_rank_floor


def order_candidates(candidates: Iterable[FusedCandidate]) -> list[FusedCandidate]:
    """The only place the final order is decided, so a reranker can replace it.
    Score descending, then sequence descending, then id ascending."""
    return sorted(
        candidates,
        key=lambda fused: (
            -fused.score,
            -fused.candidate.sequence,
            str(fused.candidate.item_id),
            fused.candidate.kind,
        ),
    )


def fuse(
    rankings: Mapping[RetrievalBranch, Sequence[Candidate]],
    *,
    rrf_k: int,
    single_branch_rank_floor: int,
) -> list[FusedCandidate]:
    """Each ranking is best first. A candidate found by only bm25 or only vector and
    ranked below `single_branch_rank_floor` there is dropped; exact-only and
    graph-only candidates are never gated."""
    candidates, ranks_by_key = _collect_ranks(rankings)
    fused = [
        FusedCandidate(candidates[key], _rrf_score(ranks, rrf_k), ranks)
        for key, ranks in ranks_by_key.items()
    ]
    kept = [item for item in fused if not _is_gated_out(item, single_branch_rank_floor)]
    return order_candidates(kept)
