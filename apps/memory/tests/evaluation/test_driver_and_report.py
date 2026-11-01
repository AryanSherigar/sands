from pathlib import Path

import pytest
from app.models.extraction import ExtractionCounts
from app.models.process_pending import ProcessPendingCounts, ProcessPendingResponse
from eval import driver, harness
from eval.driver import UsageTotals, drain
from eval.errors import BudgetExceededError, HarnessError
from eval.latency import latency_of, percentile
from eval.prices import ModelPrice, PriceTable
from eval.report import METRICS, class_summary, forbidden_exposures, format_markdown
from eval.run_models import ProbeRecord, RunReport


def _response(
    embedded: int = 0,
    applied: int = 0,
    embedding_step: str = "idle",
    extraction_step: str = "idle",
    characters: int = 0,
    input_tokens: int = 0,
) -> ProcessPendingResponse:
    return ProcessPendingResponse(
        embedding_step=embedding_step,
        counts=ProcessPendingCounts(
            spans_embedded=embedded, characters_embedded=characters
        ),
        extraction_step=extraction_step,
        extraction_counts=ExtractionCounts(
            batches_applied=applied, input_tokens=input_tokens
        ),
    )


class FakeHttp:
    def __init__(self, responses: list[ProcessPendingResponse]) -> None:
        self._responses = responses
        self.calls = 0

    async def process_pending(self, playthrough_id: object) -> ProcessPendingResponse:
        index = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return self._responses[index]


async def _no_sleep(_: float) -> None:
    return None


async def test_drain_stops_after_a_sweep_with_no_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(driver.asyncio, "sleep", _no_sleep)
    http = FakeHttp(
        [
            _response(embedded=3, characters=90),
            _response(applied=1, input_tokens=500),
            _response(),
        ]
    )
    usage = UsageTotals()
    await drain(http, None, usage, lambda _: None)  # type: ignore[arg-type]
    assert http.calls == 3
    assert usage.characters_embedded == 90 and usage.extraction_input_tokens == 500


async def test_drain_backs_off_while_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(driver.asyncio, "sleep", record_sleep)
    http = FakeHttp([_response(embedding_step="rate_limited"), _response()])
    await drain(http, None, UsageTotals(), lambda _: None)  # type: ignore[arg-type]
    assert sleeps == [driver.RATE_LIMIT_BACKOFF_SECONDS]


async def test_drain_raises_when_unconfigured() -> None:
    http = FakeHttp([_response(embedding_step="unconfigured")])
    with pytest.raises(HarnessError):
        await drain(http, None, UsageTotals(), lambda _: None)  # type: ignore[arg-type]


async def test_drain_raises_when_work_never_ends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(driver.asyncio, "sleep", _no_sleep)
    http = FakeHttp([_response(embedded=1)])
    with pytest.raises(HarnessError):
        await drain(http, None, UsageTotals(), lambda _: None)  # type: ignore[arg-type]


async def test_drain_calls_the_budget_guard_after_every_sweep() -> None:
    seen: list[int] = []
    http = FakeHttp([_response(embedded=1, characters=10), _response()])
    await drain(
        http,
        None,
        UsageTotals(),
        lambda totals: seen.append(totals.characters_embedded),
    )  # type: ignore[arg-type]
    assert seen == [10, 10]


def _record(
    arm: str,
    failure_class: str,
    found: int = 1,
    forbidden: int = 0,
    ms: float | None = None,
) -> ProbeRecord:
    return ProbeRecord(
        probe_id=f"{arm}-{failure_class}-{found}-{forbidden}",
        failure_class=failure_class,
        arm=arm,
        required_total=1,
        required_found=found,
        forbidden_count=forbidden,
        irrelevant_token_share=0.0,
        retrieve_ms=ms,
    )


def test_class_summary_marks_classes_with_too_few_probes() -> None:
    records = [
        _record("memory", "long_range"),
        _record("memory", "long_range", found=0),
    ]
    summary = class_summary(records, "memory", lambda r: float(r.required_found))
    assert summary["long_range"] is not None and summary["multi_hop"] is None


def test_forbidden_exposures_are_summed_per_arm() -> None:
    records = [
        _record("memory", "isolation", forbidden=2),
        _record("baseline", "isolation", forbidden=1),
    ]
    assert forbidden_exposures(records) == {"baseline": 1, "memory": 2}


def test_percentiles_use_nearest_rank() -> None:
    values = [float(n) for n in range(1, 101)]
    assert (percentile(values, 50), percentile(values, 95), percentile(values, 99)) == (
        50.0,
        95.0,
        99.0,
    )


def test_latency_ignores_the_baseline_arm_and_counts_skips() -> None:
    skipped = _record("memory", "long_range", ms=300.0).model_copy(
        update={"skipped_branches": ["vector"]}
    )
    latency = latency_of(
        [
            _record("baseline", "long_range"),
            _record("memory", "long_range", ms=100.0),
            skipped,
        ]
    )
    assert (
        latency is not None and latency.count == 2 and latency.skipped_branch_count == 1
    )


def _report(records: list[ProbeRecord]) -> RunReport:
    return RunReport(
        run_id="r1",
        corpus_version="1",
        content_hashes={},
        pinned={},
        is_complete=True,
        probes=records,
        unmeasured_classes=["attribution", "lore_scale"],
    )


def test_markdown_reports_forbidden_and_unmeasured_classes() -> None:
    text = format_markdown(_report([_record("memory", "isolation", forbidden=1)]))
    assert "Forbidden exposures" in text and "'memory': 1" in text
    assert "attribution, lore_scale" in text and "| isolation | memory |" in text


def test_reports_are_never_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(harness, "REPORTS_DIRECTORY", tmp_path)
    harness.write_report(_report([]))
    with pytest.raises(HarnessError):
        harness.write_report(_report([]))


def test_budget_guard_aborts_when_cost_passes_the_limit() -> None:
    from app.config import Settings

    settings = Settings()
    prices = PriceTable(
        effective_date="x",
        models={
            settings.embedding_model_name: ModelPrice(per_million_characters=1000.0),
            settings.extraction_model_name: ModelPrice(
                input_per_million_tokens=1.0, output_per_million_tokens=1.0
            ),
        },
    )
    guard = harness.make_guard(settings, prices, 2.0)
    guard(UsageTotals(characters_embedded=1000))
    with pytest.raises(BudgetExceededError):
        guard(UsageTotals(characters_embedded=5000))


def test_forbidden_only_probes_do_not_count_toward_required_evidence_metrics() -> None:
    only_forbids = ProbeRecord(
        probe_id="f",
        failure_class="isolation",
        arm="memory",
        required_total=0,
        required_found=0,
        forbidden_count=0,
        irrelevant_token_share=1.0,
    )
    with_required = _record("memory", "isolation")
    records = [
        only_forbids,
        with_required,
        with_required.model_copy(update={"probe_id": "z"}),
    ]
    summary = class_summary(records, "memory", METRICS["recall"])
    assert summary["isolation"] is not None and summary["isolation"].count == 2
    assert (
        class_summary([only_forbids], "memory", METRICS["recall"])["isolation"] is None
    )


def test_style_table_splits_direct_from_vague_probes() -> None:
    from eval.report import style_table

    direct = _record("memory", "pronoun_reference")
    vague = _record("memory", "pronoun_reference", found=0).model_copy(
        update={"style": "vague", "distractor_count": 1, "probe_id": "v1"}
    )
    table = style_table(
        [
            direct,
            direct.model_copy(update={"probe_id": "d2"}),
            vague,
            vague.model_copy(update={"probe_id": "v2"}),
        ]
    )
    assert "| direct | 2 |" in table and "| vague | 2 |" in table


def test_irrelevant_share_is_n_a_when_nothing_was_recalled() -> None:
    empty = _record("baseline", "multi_hop")
    assert METRICS["irrelevant_share"](empty) is None
    recalled = empty.model_copy(update={"recalled_tokens": 40})
    assert METRICS["irrelevant_share"](recalled) == 0.0


def test_extraction_knobs_are_handed_to_the_scratch_service() -> None:
    from app.config import Settings
    from eval.stack import _service_env

    settings = Settings(
        extraction_prompt_version="extraction_v2",
        extraction_model_name="some-model",
        extraction_thinking_level="low",
    )
    env = _service_env(
        "postgresql://x/y", "key", 10.0, harness.extraction_env(settings)
    )
    assert env["EXTRACTION_PROMPT_VERSION"] == "extraction_v2"
    assert env["EXTRACTION_MODEL_NAME"] == "some-model"
    assert env["EXTRACTION_THINKING_LEVEL"] == "low"
    default_env = harness.extraction_env(Settings())
    assert "EXTRACTION_THINKING_LEVEL" not in default_env


def test_markdown_report_lists_cost_per_turn_and_stage_timings() -> None:
    from eval.report import cost_and_timing_section
    from eval.run_models import RunReport

    report = RunReport(
        run_id="r",
        corpus_version="2",
        content_hashes={},
        pinned={},
        is_complete=True,
        cost_usd=0.06,
        turn_count=60,
        stage_ms={"bm25": 10.0, "vector": 1800.0},
        extraction_stage_ms={"llm": 2500.0},
        env_overrides={"EXTRACTION_BATCH_TURNS": "10"},
    )
    text = cost_and_timing_section(report)
    assert "$0.06000 per turn" not in text and "$0.00100 per turn" in text
    assert "bm25 10 ms" in text and "llm 2500 ms" in text and "BATCH_TURNS" in text
