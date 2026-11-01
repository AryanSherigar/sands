from pathlib import Path

import pytest
from eval import tuning
from eval.errors import BudgetExceededError
from eval.run_models import RunReport
from eval.variants import Variant, VariantRound
from pydantic import ValidationError
from tests.evaluation.test_decision import make_probe, make_report


def make_round() -> VariantRound:
    return VariantRound(
        round_id="r1",
        family="extraction_prompt_validator",
        base=Variant(
            variant_id="base", description="b", env={"EXTRACTION_BATCH_TURNS": "5"}
        ),
        variants=[
            Variant(
                variant_id="v3",
                description="d",
                env={"EXTRACTION_PROMPT_VERSION": "extraction_v2"},
            )
        ],
        repeats=2,
    )


def test_params_run_c1_on_a_dropped_scratch_db_with_the_effective_env() -> None:
    round_ = make_round()
    params = tuning.params_for(round_, round_.variants[0], 3)
    assert params.run_name == "tune-r1-v3-r3"
    assert params.campaign_ids == ["C1"] and params.should_drop_db and params.is_priced
    assert params.env_overrides == {
        "EXTRACTION_BATCH_TURNS": "5",
        "EXTRACTION_PROMPT_VERSION": "extraction_v2",
    }
    assert len(f"memory_eval_{params.run_name}") < 63


def test_ids_too_long_for_a_database_name_are_refused() -> None:
    with pytest.raises(ValidationError):
        Variant(variant_id="x" * 21, description="d")


def test_slice_spend_sums_tuning_reports_and_skips_observations(tmp_path: Path) -> None:
    def write(name: str, cost: float | None) -> None:
        report = make_report([make_probe("a", 2)]).model_copy(update={"cost_usd": cost})
        (tmp_path / name).write_text(report.model_dump_json(), encoding="utf-8")

    write("tune-r1-base-r1-20261026T010101.json", 0.04)
    write("tune-r1-v3-r1-20261026T010202.json", 0.06)
    write("baseline-20261026T212308.json", 0.12)
    (tmp_path / "tune-r1-v3-r1-20261026T010202.C1.observation.json").write_text("{}")
    assert abs(tuning.slice_spend_usd(tmp_path) - 0.10) < 1e-9


def test_budget_guard_refuses_a_run_that_could_pass_the_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tuning, "slice_spend_usd", lambda: 8.5)
    with pytest.raises(BudgetExceededError):
        tuning.assert_budget_left()
    monkeypatch.setattr(tuning, "slice_spend_usd", lambda: 7.9)
    tuning.assert_budget_left()


def test_result_of_averages_cost_per_turn_and_stage_timings() -> None:
    reports: list[RunReport] = [
        make_report([make_probe("a", 2)]).model_copy(
            update={"cost_usd": cost, "turn_count": 60, "stage_ms": {"bm25": ms}}
        )
        for cost, ms in ((0.06, 10.0), (0.12, 30.0))
    ]
    result = tuning.result_of(reports)
    assert result.cost_per_turn_usd is not None
    assert abs(result.cost_per_turn_usd - 0.0015) < 1e-9
    assert result.stage_ms == {"bm25": 20.0}
