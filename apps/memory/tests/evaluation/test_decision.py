from eval.decision import (
    ConfigResult,
    Stat,
    build_config_result,
    choose_winner,
    constraint_violations,
    dropped_probes,
    evaluate_targets,
    is_regression,
    judge_variant,
    newly_met,
    regressed_scopes,
    stat_key,
    targets_met,
)
from eval.run_models import (
    ExtractionRecord,
    IntervalOut,
    ProbeRecord,
    RunReport,
    TypeScoreOut,
)
from eval.targets import Target, TargetsFile, load_targets

RECALL_TARGET = Target(
    id="recall_long_range",
    scope="long_range",
    metric="recall",
    statistic="mean",
    comparator=">=",
    value=0.9,
    status="active",
)
FORBIDDEN_TARGET = Target(
    id="forbidden",
    scope="all_classes",
    metric="forbidden_count",
    statistic="count",
    comparator="==",
    value=0,
    status="active",
)
DEFERRED_TARGET = RECALL_TARGET.model_copy(update={"id": "later", "status": "deferred"})


def make_targets(*targets: Target) -> TargetsFile:
    return TargetsFile(source="test", corpus_version=2, targets=list(targets))


def make_probe(
    probe_id: str,
    found: int,
    failure_class: str = "long_range",
    forbidden: int = 0,
    skipped: list[str] | None = None,
) -> ProbeRecord:
    return ProbeRecord(
        probe_id=probe_id,
        failure_class=failure_class,
        arm="memory",
        required_total=2,
        required_found=found,
        forbidden_count=forbidden,
        irrelevant_token_share=0.5,
        skipped_branches=skipped or [],
    )


def make_report(
    probes: list[ProbeRecord], extraction: list[ExtractionRecord] | None = None
) -> RunReport:
    return RunReport(
        run_id="r",
        corpus_version="2",
        content_hashes={},
        pinned={},
        is_complete=True,
        probes=probes,
        extraction=extraction or [],
    )


def make_result(
    recalls: dict[str, float], cost: float | None = None, stage_ms: dict | None = None
) -> ConfigResult:
    probes = [make_probe(f"p{i}", round(r * 2)) for i, r in enumerate(recalls.values())]
    result = build_config_result([make_report(probes)], "C1", cost, stage_ms)
    return result


def test_real_targets_file_loads_with_unique_ids() -> None:
    targets = load_targets()
    ids = [t.id for t in targets.targets]
    assert len(ids) == len(set(ids))
    assert targets.active and all(t.value is not None for t in targets.active)
    assert {t.status for t in targets.targets} == {"active", "deferred"}


def test_config_result_reports_recall_and_forbidden_stats() -> None:
    probes = [make_probe("a", 2), make_probe("b", 1), make_probe("c", 2)]
    result = build_config_result([make_report(probes)], "C1")
    recall = result.stats[stat_key("long_range", "recall")]
    assert abs(recall.mean - (1.0 + 0.5 + 1.0) / 3) < 1e-9
    assert result.stats[stat_key("all_classes", "forbidden_count")].maximum == 0


def test_targets_met_counts_met_unmet_and_skips_deferred() -> None:
    result = make_result({"a": 1.0, "b": 1.0})
    targets = make_targets(RECALL_TARGET, FORBIDDEN_TARGET, DEFERRED_TARGET)
    outcomes = evaluate_targets(result, targets)
    assert [o.target_id for o in outcomes] == ["recall_long_range", "forbidden"]
    assert targets_met(outcomes) == 2


def test_target_with_no_measurement_is_unevaluated_not_met() -> None:
    result = make_result({"a": 1.0, "b": 1.0})
    missing = RECALL_TARGET.model_copy(update={"id": "x", "scope": "multi_hop"})
    outcome = evaluate_targets(result, make_targets(missing))[0]
    assert outcome.is_met is None
    assert targets_met([outcome]) == 0


def test_lower_bound_statistic_is_stricter_than_mean() -> None:
    probes = [make_probe(f"p{i}", 2) for i in range(7)] + [make_probe("z", 0)]
    result = build_config_result([make_report(probes)], "C1")
    strict = RECALL_TARGET.model_copy(update={"statistic": "lower_bound", "value": 0.8})
    assert evaluate_targets(result, make_targets(strict))[0].is_met is False


def test_point_drop_over_a_tenth_is_a_regression() -> None:
    assert is_regression([-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert not is_regression([-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert not is_regression([-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5])


def test_interval_below_zero_is_a_regression_even_for_a_small_drop() -> None:
    assert is_regression([-0.05] * 8)
    assert not is_regression([0.0] * 8)
    assert not is_regression([])


def test_regressed_scopes_and_dropped_probes_pair_by_probe_id() -> None:
    base = build_config_result(
        [make_report([make_probe(f"p{i}", 2) for i in range(4)])], "C1"
    )
    worse = build_config_result(
        [
            make_report(
                [make_probe("p0", 0), *[make_probe(f"p{i}", 2) for i in (1, 2, 3)]]
            )
        ],
        "C1",
    )
    assert regressed_scopes(worse, base) == ["long_range"]
    assert dropped_probes(worse, base) == ["p0"]
    assert regressed_scopes(base, base) == []


def test_guardrails_list_exposure_skipped_branch_and_incomplete_run() -> None:
    probes = [make_probe("a", 2, forbidden=1), make_probe("b", 2, skipped=["vector"])]
    report = make_report(probes).model_copy(update={"is_complete": False})
    failures = build_config_result([report], "C1").guardrail_failures
    assert failures == [
        "forbidden exposure",
        "incomplete run",
        "skipped retrieval branch",
    ]


def test_constraints_cost_ratio_stage_ratio_noise_floor_and_embedding_exempt() -> None:
    base = ConfigResult(
        {}, {}, [], 0.001, {"bm25": 40.0, "graph": 2.0, "vector": 100.0}
    )
    within = ConfigResult(
        {}, {}, [], 0.0015, {"bm25": 50.0, "graph": 6.0, "vector": 900.0}
    )
    assert constraint_violations(within, base) == []
    costly = ConfigResult({}, {}, [], 0.0016, {"bm25": 51.0})
    messages = constraint_violations(costly, base)
    assert any("cost" in m for m in messages) and any("bm25" in m for m in messages)


def test_constraint_breach_is_waived_only_when_a_target_becomes_met() -> None:
    targets = make_targets(RECALL_TARGET)
    base = make_result({"a": 0.5, "b": 0.5}, cost=0.001)
    better = make_result({"a": 1.0, "b": 1.0}, cost=0.002)
    same = make_result({"a": 0.5, "b": 0.5}, cost=0.002)
    assert judge_variant("better", better, base, targets).is_eligible
    verdict = judge_variant("same", same, base, targets)
    assert not verdict.is_eligible
    assert any(reason.startswith("constraint") for reason in verdict.reasons)


def test_newly_met_lists_only_targets_that_flipped() -> None:
    targets = make_targets(RECALL_TARGET, FORBIDDEN_TARGET)
    base = evaluate_targets(make_result({"a": 0.5, "b": 0.5}), targets)
    candidate = evaluate_targets(make_result({"a": 1.0, "b": 1.0}), targets)
    assert newly_met(base, candidate) == ["recall_long_range"]


def test_winner_is_base_unless_an_eligible_variant_meets_more_targets() -> None:
    targets = make_targets(RECALL_TARGET, FORBIDDEN_TARGET)
    base = make_result({"a": 0.5, "b": 0.5})
    base_verdict = judge_variant("base", base, base, targets)
    better = judge_variant("better", make_result({"a": 1.0, "b": 1.0}), base, targets)
    broken = Stat(0.0, 0.0, 1.0)
    assert choose_winner(base_verdict, [better]).variant_id == "better"
    assert choose_winner(base_verdict, []).variant_id == "base"
    assert broken.maximum == 1.0
    ineligible = better.__class__(**{**better.__dict__, "is_eligible": False})
    assert choose_winner(base_verdict, [ineligible]).variant_id == "base"


def test_extraction_recall_and_negation_stats_come_from_runs_of_one_campaign() -> None:
    def record(recall: float, negated: int, campaign: str = "C1") -> ExtractionRecord:
        score = TypeScoreOut(
            recall=IntervalOut(mean=recall, low=0.0, high=1.0, count=8),
            precision=None,
            recall_hits=1,
            label_count=8,
            predicted_count=1,
            wrong_status=0,
        )
        return ExtractionRecord(
            campaign_id=campaign,
            by_type={"fact": score},
            forbidden_extracted=0,
            duplicate_entity_rate=0.0,
            new_entity_count=0,
            negated_fact_count=negated,
        )

    reports = [
        make_report([make_probe("a", 2)], [record(0.25, 2), record(0.9, 5, "C2")]),
        make_report([make_probe("a", 2)], [record(0.75, 0)]),
    ]
    result = build_config_result(reports, "C1")
    fact = result.stats[stat_key("extraction", "fact_recall")]
    assert (fact.mean, fact.low, fact.maximum) == (0.5, 0.25, 0.75)
    negated = result.stats[stat_key("extraction", "negated_claim_stored_as_fact")]
    assert negated.maximum == 2
