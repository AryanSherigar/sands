"""Deterministic retrieval-layer scoring. A plant is satisfied when its anchor text is visible."""

import math
from collections import Counter
from dataclasses import dataclass, field

from eval.corpus_models import PlantDef, ProbeDef
from eval.scoring.claims import Claim, claim_matches, claim_of

STATE_ITEM_KINDS = frozenset({"fact", "commitment", "event"})
STATE_ONLY_CLASSES = frozenset({"knowledge_update", "rejected_mutation"})
DIAGNOSTIC_ONLY_CLASSES = frozenset({"injection"})
HIT_CUTOFFS = (1, 3, 5)
NDCG_CUTOFF = 10


@dataclass(frozen=True)
class Chunk:
    text: str
    token_count: int
    branches: tuple[str, ...] = ()
    kind: str = "span"


@dataclass(frozen=True)
class ResolvedProbe:
    probe: ProbeDef
    required_anchors: list[str]
    forbidden_anchors: list[str | None]
    forbidden_claims: list[Claim | None]
    distractor_anchors: list[str]
    distractor_claims: list[Claim | None]


@dataclass(frozen=True)
class ProbeScore:
    probe_id: str
    failure_class: str
    required_total: int
    required_found: int
    forbidden_count: int
    stale_span_count: int
    distractor_count: int
    irrelevant_token_share: float
    recalled_tokens: int = 0
    hit_at: dict[int, float] = field(default_factory=dict)
    reciprocal_rank: float = 0.0
    ndcg: float = 0.0
    branch_hits: Counter[str] = field(default_factory=Counter)
    is_graph_only_found: int = 0

    @property
    def recall(self) -> float:
        return self.required_found / self.required_total if self.required_total else 1.0


def resolve_probe(
    probe: ProbeDef, plants: dict[str, PlantDef], names: dict[str, str] | None = None
) -> ResolvedProbe:
    entity_names = names or {}
    forbidden = [plants[plant_id] for plant_id in probe.forbidden]
    return ResolvedProbe(
        probe=probe,
        required_anchors=[plants[plant_id].anchor_text for plant_id in probe.required],
        forbidden_anchors=[_forbidden_anchor(plant) for plant in forbidden]
        + probe.forbidden_anchors,
        forbidden_claims=[claim_of(plant, entity_names) for plant in forbidden]
        + [None] * len(probe.forbidden_anchors),
        distractor_anchors=[
            plants[plant_id].anchor_text for plant_id in probe.distractors
        ],
        distractor_claims=[
            claim_of(plants[plant_id], entity_names) for plant_id in probe.distractors
        ],
    )


def _forbidden_anchor(plant: PlantDef) -> str | None:
    """A negated sentence is evidence that must be recalled; only the unreal claim it denies is forbidden."""
    return None if plant.kind == "negated" else plant.anchor_text


def _first_match_index(anchor: str, chunks: list[Chunk]) -> int | None:
    for index, chunk in enumerate(chunks):
        if anchor in chunk.text:
            return index
    return None


def _is_forbidden_in(anchor: str | None, claim: Claim | None, chunk: Chunk) -> bool:
    if anchor is not None and anchor in chunk.text:
        return True
    return (
        claim is not None
        and chunk.kind in STATE_ITEM_KINDS
        and claim_matches(claim, chunk.text)
    )


def _count_forbidden(
    anchors: list[str | None], claims: list[Claim | None], recalled: list[Chunk]
) -> int:
    return sum(
        1
        for anchor, claim in zip(anchors, claims, strict=True)
        if any(_is_forbidden_in(anchor, claim, chunk) for chunk in recalled)
    )


def _split_by_class(
    failure_class: str, recalled: list[Chunk]
) -> tuple[list[Chunk], list[Chunk]]:
    """Judged chunks, then diagnostic chunks. For knowledge_update and rejected_mutation
    only items presented as current state are judged; narration spans are history."""
    if failure_class in DIAGNOSTIC_ONLY_CLASSES:
        return [], recalled
    if failure_class not in STATE_ONLY_CLASSES:
        return recalled, []
    judged = [chunk for chunk in recalled if chunk.kind in STATE_ITEM_KINDS]
    return judged, [chunk for chunk in recalled if chunk.kind not in STATE_ITEM_KINDS]


def _irrelevant_share(required: list[str], recalled: list[Chunk]) -> float:
    total = sum(chunk.token_count for chunk in recalled)
    if total == 0:
        return 0.0
    irrelevant = sum(
        chunk.token_count
        for chunk in recalled
        if not any(anchor in chunk.text for anchor in required)
    )
    return irrelevant / total


def _ndcg(required: list[str], recalled: list[Chunk]) -> float:
    """Binary gain, counted once per required plant: a second item repeating a
    plant already found adds nothing, so the score can never exceed 1."""
    matched: set[str] = set()
    gains: list[float] = []
    for chunk in recalled[:NDCG_CUTOFF]:
        fresh = {a for a in required if a not in matched and a in chunk.text}
        matched |= fresh
        gains.append(1.0 if fresh else 0.0)
    dcg = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(gains))
    ideal_count = min(len(required), NDCG_CUTOFF)
    ideal = sum(1.0 / math.log2(rank + 2) for rank in range(ideal_count))
    return dcg / ideal if ideal else 0.0


def _rank_metrics(
    required: list[str], recalled: list[Chunk]
) -> tuple[dict[int, float], float]:
    indexes = [_first_match_index(anchor, recalled) for anchor in required]
    found = [index for index in indexes if index is not None]
    first = min(found) if found else None
    hits = {
        cutoff: 1.0 if first is not None and first < cutoff else 0.0
        for cutoff in HIT_CUTOFFS
    }
    return hits, (1.0 / (first + 1) if first is not None else 0.0)


def _branch_attribution(
    required: list[str], recalled: list[Chunk]
) -> tuple[Counter[str], int]:
    hits: Counter[str] = Counter()
    graph_only = 0
    for anchor in required:
        index = _first_match_index(anchor, recalled)
        if index is None:
            continue
        branches = recalled[index].branches
        hits.update(branches)
        graph_only += 1 if branches == ("graph",) else 0
    return hits, graph_only


def _exposure_counts(
    resolved: ResolvedProbe, recalled: list[Chunk]
) -> tuple[int, int, int]:
    """Forbidden (judged), stale-span (diagnostic) and wrong-referent counts."""
    judged, diagnostic = _split_by_class(resolved.probe.failure_class, recalled)
    anchors, claims = resolved.forbidden_anchors, resolved.forbidden_claims
    return (
        _count_forbidden(anchors, claims, judged),
        _count_forbidden(anchors, claims, diagnostic),
        _count_forbidden(
            resolved.distractor_anchors, resolved.distractor_claims, recalled
        ),
    )


def score_probe(
    resolved: ResolvedProbe, visible_text: str, recalled: list[Chunk]
) -> ProbeScore:
    """`visible_text` is everything the narrator sees; `recalled` is the ranked recall only."""
    required = resolved.required_anchors
    hits, reciprocal_rank = _rank_metrics(required, recalled)
    branch_hits, graph_only = _branch_attribution(required, recalled)
    forbidden, stale, distractor = _exposure_counts(resolved, recalled)
    return ProbeScore(
        probe_id=resolved.probe.probe_id,
        failure_class=resolved.probe.failure_class,
        required_total=len(required),
        required_found=sum(1 for anchor in required if anchor in visible_text),
        forbidden_count=forbidden,
        stale_span_count=stale,
        distractor_count=distractor,
        irrelevant_token_share=_irrelevant_share(required, recalled),
        recalled_tokens=sum(chunk.token_count for chunk in recalled),
        hit_at=hits,
        reciprocal_rank=reciprocal_rank,
        ndcg=_ndcg(required, recalled),
        branch_hits=branch_hits,
        is_graph_only_found=graph_only,
    )
