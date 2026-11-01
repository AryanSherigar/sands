"""Per-class aggregation and the markdown tables of a run report."""

from collections.abc import Callable

from eval.corpus_models import MEASURED_CLASSES
from eval.run_models import IntervalOut, ProbeRecord, RunReport
from eval.scoring.stats import bootstrap_interval

ARM_ORDER = ("baseline", "memory")
HIT_CUTOFF_FOR_TABLE = 5
MetricFn = Callable[[ProbeRecord], float | None]


def _if_required(value: Callable[[ProbeRecord], float | None]) -> MetricFn:
    """Required-evidence metrics are undefined for probes that only forbid."""
    return lambda r: value(r) if r.required_total else None


METRICS: dict[str, MetricFn] = {
    "recall": _if_required(lambda r: r.required_found / r.required_total),
    "forbidden_rate": lambda r: 1.0 if r.forbidden_count else 0.0,
    "stale_span_rate": lambda r: 1.0 if r.stale_span_count else 0.0,
    "distractor_rate": lambda r: 1.0 if r.distractor_count else 0.0,
    "irrelevant_share": _if_required(
        lambda r: r.irrelevant_token_share if r.recalled_tokens else None
    ),
    "hit_at_5": _if_required(lambda r: r.hit_at.get(HIT_CUTOFF_FOR_TABLE, 0.0)),
    "mrr": _if_required(lambda r: r.reciprocal_rank),
    "ndcg": _if_required(lambda r: r.ndcg),
}


def interval_out(values: list[float]) -> IntervalOut | None:
    interval = bootstrap_interval(values)
    if interval is None:
        return None
    return IntervalOut(
        mean=interval.mean, low=interval.low, high=interval.high, count=interval.count
    )


def metric_values(
    records: list[ProbeRecord], arm: str, name: str, metric: MetricFn
) -> list[float]:
    scored = (metric(r) for r in records if r.arm == arm and r.failure_class == name)
    return [value for value in scored if value is not None]


def class_summary(
    records: list[ProbeRecord], arm: str, metric: MetricFn
) -> dict[str, IntervalOut | None]:
    return {
        name: interval_out(metric_values(records, arm, name, metric))
        for name in MEASURED_CLASSES
    }


def _cell(interval: IntervalOut | None, count: int) -> str:
    if interval is None:
        return f"n={count} (too few)" if count else "-"
    return f"{interval.mean:.2f} [{interval.low:.2f}, {interval.high:.2f}]"


def _row(records: list[ProbeRecord], name: str, arm: str) -> str:
    count = sum(1 for r in records if r.arm == arm and r.failure_class == name)
    cells = []
    for metric in METRICS.values():
        values = metric_values(records, arm, name, metric)
        cells.append(_cell(interval_out(values), len(values)))
    return f"| {name} | {arm} | {count} | " + " | ".join(cells) + " |"


def retrieval_table(records: list[ProbeRecord]) -> str:
    header = "| class | arm | probes | " + " | ".join(METRICS) + " |"
    divider = "|" + "---|" * (len(METRICS) + 3)
    rows = [_row(records, name, arm) for name in MEASURED_CLASSES for arm in ARM_ORDER]
    return "\n".join([header, divider, *rows])


def style_table(records: list[ProbeRecord]) -> str:
    """Memory-arm recall and wrong-referent rate split by how the probe is phrased."""
    lines = ["| style | probes | recall | distractor_rate |", "|---|---|---|---|"]
    for style in ("direct", "vague"):
        memory = [r for r in records if r.arm == "memory" and r.style == style]
        recall = [m for m in (METRICS["recall"](r) for r in memory) if m is not None]
        distractor = [float(bool(r.distractor_count)) for r in memory]
        cells = [interval_out(recall), interval_out(distractor)]
        lines.append(
            f"| {style} | {len(memory)} | {_cell(cells[0], len(recall))} | "
            f"{_cell(cells[1], len(distractor))} |"
        )
    return "\n".join(lines)


def forbidden_exposures(records: list[ProbeRecord]) -> dict[str, int]:
    return {
        arm: sum(r.forbidden_count for r in records if r.arm == arm)
        for arm in ARM_ORDER
    }


def extraction_table(report: RunReport) -> str:
    lines = [
        "| campaign | type | labels | recall | predicted | precision | wrong status |",
        "|---|---|---|---|---|---|---|",
    ]
    for record in report.extraction:
        for name, score in record.by_type.items():
            lines.append(
                f"| {record.campaign_id} | {name} | {score.label_count} | "
                f"{_cell(score.recall, score.label_count)} | {score.predicted_count} | "
                f"{_cell(score.precision, score.predicted_count)} | {score.wrong_status} |"
            )
    return "\n".join(lines)


def _stage_row(label: str, stage_ms: dict[str, float]) -> str:
    cells = ", ".join(f"{name} {millis:.0f} ms" for name, millis in stage_ms.items())
    return f"- {label}: {cells or 'none recorded'}"


def cost_and_timing_section(report: RunReport) -> str:
    """Laptop timings: the vector stage is the embedding call and is network-bound."""
    cost = "unpriced" if report.cost_usd is None else f"${report.cost_usd:.4f}"
    per_turn = ""
    if report.cost_usd is not None and report.turn_count:
        per_turn = f" (${report.cost_usd / report.turn_count:.5f} per turn)"
    lines = [
        f"- Cost: {cost}{per_turn} over {report.turn_count} turns.",
        _stage_row("Retrieval stages, mean per call", report.stage_ms),
        _stage_row("Extraction steps, mean per batch", report.extraction_stage_ms),
    ]
    if report.env_overrides:
        lines.append(f"- Overrides: {report.env_overrides}")
    return "\n".join(lines)


def format_markdown(report: RunReport) -> str:
    exposures = forbidden_exposures(report.probes)
    sections = [
        f"# Memory evaluation run {report.run_id}",
        f"Corpus {report.corpus_version}; complete: {report.is_complete}.",
        f"Not yet measured: {', '.join(report.unmeasured_classes)}.",
        "## Retrieval layer (per class, mean [95% bootstrap interval])",
        retrieval_table(report.probes),
        f"Forbidden exposures (release-blocking, never averaged): {exposures}.",
        "## Direct versus vague probes (memory arm)",
        style_table(report.probes),
        "## Extraction layer",
        extraction_table(report),
        "## Cost and timings (laptop, not cloud)",
        cost_and_timing_section(report),
    ]
    return "\n\n".join(sections) + "\n"
