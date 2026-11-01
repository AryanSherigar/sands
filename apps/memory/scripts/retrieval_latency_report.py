"""Prints the measured results of a retrieval latency run."""

from dataclasses import dataclass

from scripts.retrieval_latency_index import CorpusCounts, IndexResult
from scripts.retrieval_latency_run import RunResult
from scripts.retrieval_latency_stats import (
    BRANCHES,
    PERCENTILE_P50,
    PERCENTILE_P95,
    BranchSummary,
    LatencySummary,
    percentile,
    stage_names,
    stage_samples,
    summarize_latency,
    unstaged_samples,
    zero_result_branches,
)
from scripts.retrieval_latency_types import BuiltCorpus

TARGET_P95_MS = 150.0
UNSTAGED_LABEL = "unstaged"
COLUMN_WIDTH = 12


@dataclass(frozen=True)
class CorpusReport:
    name: str
    latency: LatencySummary
    stage_p95: dict[str, float]
    stage_p50: dict[str, float]


def print_counts(
    corpus: BuiltCorpus,
    counts: CorpusCounts,
    deviation: float | None,
    timings: tuple[float, IndexResult],
) -> None:
    build_seconds, index = timings
    print(f"\n=== corpus {corpus.spec.name} ({corpus.spec.mode}) ===")
    print(
        f"build {build_seconds:.1f}s; embed {index.seconds:.1f}s in {index.sweeps} sweeps"
    )
    print(
        f"spans={counts.spans} facts={counts.facts} "
        f"embeddings(active model)={counts.embeddings} "
        f"hidden={counts.hidden} conditional={counts.conditional}"
    )
    print(
        f"entities={counts.entities} aliases={counts.aliases} "
        f"relation_facts={counts.relations} hubs(>20 edges)={counts.hubs} "
        f"max_entity_degree={counts.max_degree}"
    )
    print(
        f"commitments={counts.commitments} resolved={counts.commitment_statuses} "
        f"ingested_turns={counts.ingested_turns} indexed_turns={counts.indexed_turns}"
    )
    print(_size_line(corpus, counts, deviation))


def _size_line(
    corpus: BuiltCorpus, counts: CorpusCounts, deviation: float | None
) -> str:
    if deviation is None:
        return f"size check: no intended size; {counts.embeddings} embedded (all spans+facts)"
    return (
        f"size check: intended {corpus.spec.target_embeddable}, embedded "
        f"{counts.embeddings} ({deviation:+.1%}) OK"
    )


def print_branch_stats(summary: BranchSummary, run: RunResult) -> None:
    print(f"queries measured: {summary.query_count}; kinds: {dict(run.kinds)}")
    print(
        f"mean packed items/response: {summary.mean_items:.1f}; "
        f"mean seeds/query: {summary.mean_seed_count:.1f}; "
        f"queries with zero seeds: {summary.zero_seed_queries}"
    )
    for branch in BRANCHES:
        print(
            f"  {branch:<7} responses with packed items: "
            f"{summary.responses_with_items[branch]:>3}; responses with candidates: "
            f"{summary.responses_with_candidates[branch]:>3}; "
            f"mean candidates: {summary.mean_candidates[branch]:.1f}"
        )
    print(f"degraded reasons seen: {dict(summary.degraded_reasons) or 'none'}")
    for branch in zero_result_branches(summary):
        print(f"WARNING: branch '{branch}' produced zero results in this corpus run")


def build_report(name: str, run: RunResult) -> CorpusReport:
    stages = stage_names(run.logs)
    samples = {stage: stage_samples(run.logs, stage) for stage in stages}
    samples[UNSTAGED_LABEL] = unstaged_samples(run.latencies_ms, run.logs)
    return CorpusReport(
        name=name,
        latency=summarize_latency(run.latencies_ms),
        stage_p95={s: percentile(v, PERCENTILE_P95) for s, v in samples.items()},
        stage_p50={s: percentile(v, PERCENTILE_P50) for s, v in samples.items()},
    )


def print_latency_table(reports: list[CorpusReport]) -> None:
    print("\n=== latency (ms), embedding call faked at ~0 ms ===")
    header = ["corpus", "p50", "p95", "p99", "max", "p95<=150ms"]
    print("".join(f"{cell:<{COLUMN_WIDTH}}" for cell in header))
    for report in reports:
        latency = report.latency
        verdict = "PASS" if latency.p95 <= TARGET_P95_MS else "FAIL"
        cells = [report.name, *(f"{v:.1f}" for v in _latency_values(latency)), verdict]
        print("".join(f"{cell:<{COLUMN_WIDTH}}" for cell in cells))
    print(f"(soft target p95 <= {TARGET_P95_MS:.0f} ms is informational only)")


def _latency_values(latency: LatencySummary) -> list[float]:
    return [latency.p50, latency.p95, latency.p99, latency.maximum]


def print_stage_table(reports: list[CorpusReport]) -> None:
    print("\n=== per-stage ms from the retrieve_completed log line (p50 / p95) ===")
    print("stage timings are rounded to whole ms by the service; 'unstaged' is")
    print("total latency minus the logged stage sum (snapshot, playthrough load,")
    print("degraded check, response assembly), so it carries that rounding.")
    print(
        f"{'stage':<{COLUMN_WIDTH}}"
        + "".join(f"{r.name:<{COLUMN_WIDTH + 6}}" for r in reports)
    )
    stages = list(dict.fromkeys(s for report in reports for s in report.stage_p95))
    for stage in stages:
        cells = [_stage_cell(report, stage) for report in reports]
        print(
            f"{stage:<{COLUMN_WIDTH}}"
            + "".join(f"{c:<{COLUMN_WIDTH + 6}}" for c in cells)
        )


def _stage_cell(report: CorpusReport, stage: str) -> str:
    if stage not in report.stage_p95:
        return "-"
    return f"{report.stage_p50[stage]:.1f} / {report.stage_p95[stage]:.1f}"
