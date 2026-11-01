"""Latency statistics of recorded retrieval calls."""

import math

from eval.run_models import LatencyRecord, ProbeRecord

MEMORY_ARM = "memory"
P50, P95, P99 = 50, 95, 99


def percentile(values: list[float], percent: int) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(percent / 100 * len(ordered)))
    return ordered[rank - 1]


def latency_of(records: list[ProbeRecord]) -> LatencyRecord | None:
    memory = [r for r in records if r.arm == MEMORY_ARM and r.retrieve_ms is not None]
    if not memory:
        return None
    timings = [r.retrieve_ms for r in memory if r.retrieve_ms is not None]
    return LatencyRecord(
        p50_ms=percentile(timings, P50),
        p95_ms=percentile(timings, P95),
        p99_ms=percentile(timings, P99),
        count=len(timings),
        skipped_branch_count=sum(1 for r in memory if r.skipped_branches),
    )
