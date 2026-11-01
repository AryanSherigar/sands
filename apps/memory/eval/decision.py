"""The tuning decision rule: guardrails, no regression, targets met, cost and stage limits.

Pure: reads run reports and the accepted targets, never touches a database or a model.
"""

import statistics
from collections.abc import Iterator
from dataclasses import dataclass, field

from eval.report import METRICS, MetricFn
from eval.run_models import ExtractionRecord, ProbeRecord, RunReport
from eval.scoring.stats import bootstrap_interval
from eval.targets import Target, TargetsFile

MEMORY_ARM = "memory"
REGRESSION_DROP = 0.10
COST_LIMIT_RATIO = 1.5
STAGE_LIMIT_RATIO = 1.25
STAGE_NOISE_FLOOR_MS = 5.0
EMBEDDING_STAGES = frozenset({"vector"})
EXTRACTION_SCOPE = "extraction"
EXTRACTION_RECALL_TYPES = ("fact", "commitment", "supersession")
PRONOUN_CLASS = "pronoun_reference"
ALL_CLASSES_SCOPE = "all_classes"
FLOAT_TOLERANCE = 1e-9
STAT_FIELD = {
    "lower_bound": "low",
    "mean": "mean",
    "mean_over_runs": "mean",
    "max_over_runs": "maximum",
    "count": "maximum",
}


@dataclass(frozen=True)
class Stat:
    mean: float
    low: float
    maximum: float


@dataclass(frozen=True)
class ConfigResult:
    stats: dict[str, Stat]
    per_probe: dict[str, dict[str, float]]
    guardrail_failures: list[str]
    cost_per_turn_usd: float | None = None
    stage_ms: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TargetOutcome:
    target_id: str
    value: float | None
    is_met: bool | None


@dataclass(frozen=True)
class Verdict:
    variant_id: str
    is_eligible: bool
    reasons: list[str]
    targets_met: int
    extraction_gain: int
    worst_class_low: float
    cost_per_turn_usd: float | None
    dropped_probes: list[str]


def stat_key(scope: str, metric: str) -> str:
    return f"{scope}|{metric}"


def stat_of_runs(values: list[float]) -> Stat:
    return Stat(statistics.fmean(values), min(values), max(values))


def stat_of_probes(values: list[float]) -> Stat:
    interval = bootstrap_interval(values)
    low = interval.low if interval else min(values)
    return Stat(statistics.fmean(values), low, max(values))


def scopes_of(record: ProbeRecord) -> list[str]:
    scopes = [record.failure_class]
    if record.failure_class == PRONOUN_CLASS:
        scopes.append(f"{PRONOUN_CLASS}:{record.style}")
    return scopes


def _memory_records(reports: list[RunReport]) -> Iterator[ProbeRecord]:
    for report in reports:
        yield from (r for r in report.probes if r.arm == MEMORY_ARM)


def probe_means(
    reports: list[RunReport], metric: MetricFn
) -> dict[str, dict[str, float]]:
    samples: dict[str, dict[str, list[float]]] = {}
    for record in _memory_records(reports):
        value = metric(record)
        if value is None:
            continue
        for scope in scopes_of(record):
            samples.setdefault(scope, {}).setdefault(record.probe_id, []).append(value)
    return {
        scope: {pid: statistics.fmean(values) for pid, values in probes.items()}
        for scope, probes in samples.items()
    }


def _retrieval_stats(reports: list[RunReport]) -> dict[str, Stat]:
    stats: dict[str, Stat] = {}
    for metric_name in ("recall", "distractor_rate"):
        means = probe_means(reports, METRICS[metric_name])
        for scope, probes in means.items():
            stats[stat_key(scope, metric_name)] = stat_of_probes(list(probes.values()))
    return stats


def _forbidden_stat(reports: list[RunReport]) -> Stat:
    totals = [float(sum(r.forbidden_count for r in rep.probes)) for rep in reports]
    return stat_of_runs(totals)


def _extraction_records(
    reports: list[RunReport], campaign_id: str
) -> list[ExtractionRecord]:
    return [
        record
        for report in reports
        for record in report.extraction
        if record.campaign_id == campaign_id
    ]


def _recall_per_run(records: list[ExtractionRecord], name: str) -> list[float]:
    scores = [record.by_type.get(name) for record in records]
    return [score.recall.mean for score in scores if score and score.recall]


def _extraction_stats(reports: list[RunReport], campaign_id: str) -> dict[str, Stat]:
    records = _extraction_records(reports, campaign_id)
    stats: dict[str, Stat] = {}
    for name in EXTRACTION_RECALL_TYPES:
        values = _recall_per_run(records, name)
        if values:
            stats[stat_key(EXTRACTION_SCOPE, f"{name}_recall")] = stat_of_runs(values)
    if records:
        negated = [float(record.negated_fact_count) for record in records]
        key = stat_key(EXTRACTION_SCOPE, "negated_claim_stored_as_fact")
        stats[key] = stat_of_runs(negated)
    return stats


def guardrail_failures_of(reports: list[RunReport]) -> list[str]:
    failures: set[str] = set()
    for report in reports:
        if not report.is_complete:
            failures.add("incomplete run")
    for record in _memory_records(reports):
        if record.forbidden_count:
            failures.add("forbidden exposure")
        if record.skipped_branches:
            failures.add("skipped retrieval branch")
        if record.degraded_reasons:
            failures.add("degraded retrieval")
    return sorted(failures)


def build_config_result(
    reports: list[RunReport],
    campaign_id: str,
    cost_per_turn_usd: float | None = None,
    stage_ms: dict[str, float] | None = None,
) -> ConfigResult:
    stats = {
        **_retrieval_stats(reports),
        **_extraction_stats(reports, campaign_id),
        stat_key(ALL_CLASSES_SCOPE, "forbidden_count"): _forbidden_stat(reports),
    }
    return ConfigResult(
        stats=stats,
        per_probe=probe_means(reports, METRICS["recall"]),
        guardrail_failures=guardrail_failures_of(reports),
        cost_per_turn_usd=cost_per_turn_usd,
        stage_ms=stage_ms or {},
    )


def _is_met(target: Target, value: float) -> bool:
    limit = target.value if target.value is not None else value
    if target.comparator == ">=":
        return value >= limit - FLOAT_TOLERANCE
    if target.comparator == "<=":
        return value <= limit + FLOAT_TOLERANCE
    return abs(value - limit) <= FLOAT_TOLERANCE


def evaluate_targets(result: ConfigResult, targets: TargetsFile) -> list[TargetOutcome]:
    outcomes: list[TargetOutcome] = []
    for target in targets.active:
        stat = result.stats.get(stat_key(target.scope, target.metric))
        if stat is None:
            outcomes.append(TargetOutcome(target.id, None, None))
            continue
        value = getattr(stat, STAT_FIELD[target.statistic])
        outcomes.append(TargetOutcome(target.id, value, _is_met(target, value)))
    return outcomes


def targets_met(outcomes: list[TargetOutcome]) -> int:
    return sum(1 for outcome in outcomes if outcome.is_met)


def newly_met(base: list[TargetOutcome], candidate: list[TargetOutcome]) -> list[str]:
    was_met = {o.target_id for o in base if o.is_met}
    return [o.target_id for o in candidate if o.is_met and o.target_id not in was_met]


def is_regression(differences: list[float]) -> bool:
    if not differences:
        return False
    if statistics.fmean(differences) < -REGRESSION_DROP:
        return True
    interval = bootstrap_interval(differences)
    return interval is not None and interval.high < 0


def paired_differences(
    candidate: dict[str, float], base: dict[str, float]
) -> list[float]:
    return [candidate[pid] - base[pid] for pid in candidate if pid in base]


def regressed_scopes(candidate: ConfigResult, base: ConfigResult) -> list[str]:
    return sorted(
        scope
        for scope, probes in candidate.per_probe.items()
        if is_regression(paired_differences(probes, base.per_probe.get(scope, {})))
    )


def dropped_probes(candidate: ConfigResult, base: ConfigResult) -> list[str]:
    dropped: set[str] = set()
    for scope, probes in candidate.per_probe.items():
        base_probes = base.per_probe.get(scope, {})
        dropped.update(
            pid
            for pid, value in probes.items()
            if pid in base_probes and value < base_probes[pid] - FLOAT_TOLERANCE
        )
    return sorted(dropped)


def _stage_violation(stage: str, millis: float, base: dict[str, float]) -> str | None:
    base_millis = base.get(stage)
    if stage in EMBEDDING_STAGES or base_millis is None:
        return None
    is_slower = millis > base_millis * STAGE_LIMIT_RATIO
    if is_slower and millis - base_millis > STAGE_NOISE_FLOOR_MS:
        return f"stage {stage} {millis:.0f} ms against {base_millis:.0f} ms"
    return None


def constraint_violations(candidate: ConfigResult, base: ConfigResult) -> list[str]:
    violations: list[str] = []
    cost, base_cost = candidate.cost_per_turn_usd, base.cost_per_turn_usd
    if cost is not None and base_cost and cost > base_cost * COST_LIMIT_RATIO:
        violations.append(f"cost {cost / base_cost:.2f}x the carried-forward config")
    for stage, millis in sorted(candidate.stage_ms.items()):
        message = _stage_violation(stage, millis, base.stage_ms)
        if message:
            violations.append(message)
    return violations


def extraction_gain(candidate: ConfigResult, base: ConfigResult) -> int:
    gain = 0
    for key, stat in candidate.stats.items():
        base_stat = base.stats.get(key)
        if (
            key.startswith(EXTRACTION_SCOPE)
            and base_stat
            and stat.low > base_stat.maximum
        ):
            gain += 1
    return gain


def worst_class_low(result: ConfigResult) -> float:
    lows = [
        stat.low
        for key, stat in result.stats.items()
        if key.endswith("|recall")
        and ":" not in key
        and not key.startswith(EXTRACTION_SCOPE)
    ]
    return min(lows) if lows else 0.0


def judge_variant(
    variant_id: str, candidate: ConfigResult, base: ConfigResult, targets: TargetsFile
) -> Verdict:
    base_outcomes = evaluate_targets(base, targets)
    outcomes = evaluate_targets(candidate, targets)
    reasons = [f"guardrail: {f}" for f in candidate.guardrail_failures]
    reasons += [f"regression: {s}" for s in regressed_scopes(candidate, base)]
    violations = constraint_violations(candidate, base)
    if violations and not newly_met(base_outcomes, outcomes):
        reasons += [f"constraint: {v}" for v in violations]
    return Verdict(
        variant_id=variant_id,
        is_eligible=not reasons,
        reasons=reasons,
        targets_met=targets_met(outcomes),
        extraction_gain=extraction_gain(candidate, base),
        worst_class_low=worst_class_low(candidate),
        cost_per_turn_usd=candidate.cost_per_turn_usd,
        dropped_probes=dropped_probes(candidate, base),
    )


def _ranking_key(verdict: Verdict) -> tuple[float, float, float, float]:
    cost = verdict.cost_per_turn_usd if verdict.cost_per_turn_usd is not None else 0.0
    return (
        -verdict.targets_met,
        -verdict.extraction_gain,
        -verdict.worst_class_low,
        cost,
    )


def choose_winner(base_verdict: Verdict, verdicts: list[Verdict]) -> Verdict:
    eligible = [v for v in verdicts if v.is_eligible]
    if not eligible:
        return base_verdict
    best = min(eligible, key=_ranking_key)
    return best if _ranking_key(best) < _ranking_key(base_verdict) else base_verdict
