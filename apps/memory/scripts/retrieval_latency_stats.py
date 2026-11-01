"""Pure statistics over a retrieval run: percentiles, branch presence, stage timings."""

import math
from collections import Counter
from dataclasses import dataclass

from app.models.retrieve import RetrieveResponse

BRANCHES = ["exact", "bm25", "vector", "graph"]
PERCENTILE_P50 = 50
PERCENTILE_P95 = 95
PERCENTILE_P99 = 99
PERCENT = 100
MILLISECONDS_PER_SECOND = 1000


@dataclass(frozen=True)
class LatencySummary:
    p50: float
    p95: float
    p99: float
    maximum: float


@dataclass(frozen=True)
class BranchSummary:
    query_count: int
    mean_items: float
    mean_seed_count: float
    zero_seed_queries: int
    responses_with_items: dict[str, int]
    responses_with_candidates: dict[str, int]
    mean_candidates: dict[str, float]
    degraded_reasons: Counter[str]


def percentile(values: list[float], pct: int) -> float:
    """Nearest-rank percentile with the rank clamped to the last index."""
    ordered = sorted(values)
    rank = math.ceil(pct / PERCENT * len(ordered)) - 1
    return ordered[min(max(rank, 0), len(ordered) - 1)]


def summarize_latency(latencies_ms: list[float]) -> LatencySummary:
    return LatencySummary(
        p50=percentile(latencies_ms, PERCENTILE_P50),
        p95=percentile(latencies_ms, PERCENTILE_P95),
        p99=percentile(latencies_ms, PERCENTILE_P99),
        maximum=max(latencies_ms),
    )


def _mean(values: list[int]) -> float:
    return sum(values) / len(values)


def summarize_branches(
    responses: list[RetrieveResponse], logs: list[dict[str, object]]
) -> BranchSummary:
    seed_counts = [int(str(entry["seed_count"])) for entry in logs]
    candidate_counts = [_branch_counts(entry) for entry in logs]
    return BranchSummary(
        query_count=len(responses),
        mean_items=_mean([len(response.items) for response in responses]),
        mean_seed_count=_mean(seed_counts),
        zero_seed_queries=sum(1 for count in seed_counts if count == 0),
        responses_with_items={
            branch: sum(
                1
                for response in responses
                if any(branch in item.branches for item in response.items)
            )
            for branch in BRANCHES
        },
        responses_with_candidates={
            branch: sum(1 for counts in candidate_counts if counts.get(branch, 0) > 0)
            for branch in BRANCHES
        },
        mean_candidates={
            branch: _mean([counts.get(branch, 0) for counts in candidate_counts])
            for branch in BRANCHES
        },
        degraded_reasons=Counter(
            reason for response in responses for reason in response.degraded_reasons
        ),
    )


def _branch_counts(entry: dict[str, object]) -> dict[str, int]:
    counts = entry["branch_counts"]
    if not isinstance(counts, dict):
        raise TypeError("branch_counts is not a mapping")
    return {str(branch): int(count) for branch, count in counts.items()}


def stage_names(logs: list[dict[str, object]]) -> list[str]:
    names: dict[str, None] = {}
    for entry in logs:
        names.update(dict.fromkeys(_stage_ms(entry)))
    return list(names)


def _stage_ms(entry: dict[str, object]) -> dict[str, int]:
    stages = entry["stage_ms"]
    if not isinstance(stages, dict):
        raise TypeError("stage_ms is not a mapping")
    return {str(stage): int(value) for stage, value in stages.items()}


def stage_samples(logs: list[dict[str, object]], stage: str) -> list[float]:
    return [float(_stage_ms(entry).get(stage, 0)) for entry in logs]


def unstaged_samples(
    latencies_ms: list[float], logs: list[dict[str, object]]
) -> list[float]:
    return [
        latency - sum(_stage_ms(entry).values())
        for latency, entry in zip(latencies_ms, logs, strict=True)
    ]


def zero_result_branches(summary: BranchSummary) -> list[str]:
    return [
        branch
        for branch in BRANCHES
        if summary.responses_with_items[branch] == 0
        or summary.responses_with_candidates[branch] == 0
    ]
