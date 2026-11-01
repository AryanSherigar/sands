"""CLI: `python -m eval.tuning --round eval/rounds/r1.json` runs one pre-registered round."""

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from eval.decision import (
    ConfigResult,
    Verdict,
    build_config_result,
    choose_winner,
    judge_variant,
)
from eval.errors import BudgetExceededError, HarnessError
from eval.harness import REPORTS_DIRECTORY, RunParams, execute_run
from eval.run_models import RunReport
from eval.targets import TargetsFile, load_targets
from eval.variants import (
    Variant,
    VariantRound,
    load_round,
    record_result,
    register_round,
)

TUNING_CAMPAIGN = "C1"
TOTAL_BUDGET_USD = 10.0
PER_RUN_BUDGET_USD = 2.0
RUN_PREFIX = "tune"
SPEND_SCAN_PATTERN = f"{RUN_PREFIX}-*.json"


def run_name_of(round_id: str, variant_id: str, repeat: int) -> str:
    return f"{RUN_PREFIX}-{round_id}-{variant_id}-r{repeat}"


def slice_spend_usd(directory: Path = REPORTS_DIRECTORY) -> float:
    spend = 0.0
    for path in directory.glob(SPEND_SCAN_PATTERN):
        if path.name.endswith(".observation.json"):
            continue
        cost = RunReport.model_validate_json(path.read_text(encoding="utf-8")).cost_usd
        spend += cost or 0.0
    return spend


def assert_budget_left() -> None:
    spent = slice_spend_usd()
    if spent + PER_RUN_BUDGET_USD > TOTAL_BUDGET_USD:
        raise BudgetExceededError(
            f"Slice spend ${spent:.2f} leaves less than one run's "
            f"${PER_RUN_BUDGET_USD:.2f} limit under the ${TOTAL_BUDGET_USD:.2f} total"
        )


def params_for(round_: VariantRound, variant: Variant, repeat: int) -> RunParams:
    return RunParams(
        corpus_root=Path("eval/corpus"),
        campaign_ids=[TUNING_CAMPAIGN],
        run_name=run_name_of(round_.round_id, variant.variant_id, repeat),
        budget_usd=PER_RUN_BUDGET_USD,
        is_priced=True,
        is_minimum_enforced=False,
        is_freeze_enforced=True,
        should_drop_db=True,
        env_overrides=round_.effective_env(variant),
    )


async def run_variant(round_: VariantRound, variant: Variant) -> list[RunReport]:
    reports: list[RunReport] = []
    for repeat in range(1, round_.repeats + 1):
        assert_budget_left()
        report, _ = await execute_run(params_for(round_, variant, repeat))
        reports.append(report)
    return reports


def result_of(reports: list[RunReport]) -> ConfigResult:
    costs = [r.cost_usd for r in reports if r.cost_usd is not None]
    turns = reports[0].turn_count or 1
    per_turn = sum(costs) / len(costs) / turns if costs else None
    stages = {
        stage: sum(r.stage_ms.get(stage, 0.0) for r in reports) / len(reports)
        for stage in {name for r in reports for name in r.stage_ms}
    }
    return build_config_result(reports, TUNING_CAMPAIGN, per_turn, stages)


def write_round_report(
    round_: VariantRound,
    verdicts: list[Verdict],
    winner: Verdict,
    run_ids: dict[str, list[str]],
) -> Path:
    path = REPORTS_DIRECTORY / f"round-{round_.round_id}.json"
    if path.exists():
        raise HarnessError(f"Round report {path.name} already exists")
    payload = {
        "round_id": round_.round_id,
        "family": round_.family,
        "base": round_.base.variant_id,
        "winner": winner.variant_id,
        "run_ids": run_ids,
        "verdicts": [asdict(verdict) for verdict in verdicts],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def summarize(winner: Verdict, base_id: str) -> str:
    kept = "kept the base" if winner.variant_id == base_id else "new winner"
    return f"{kept}: {winner.variant_id} meeting {winner.targets_met} targets"


def load_reports(run_ids: list[str]) -> list[RunReport]:
    paths = [REPORTS_DIRECTORY / f"{run_id}.json" for run_id in run_ids]
    return [RunReport.model_validate_json(p.read_text(encoding="utf-8")) for p in paths]


async def run_round(round_: VariantRound, targets: TargetsFile) -> Path:
    register_round(round_)
    base_reports = load_reports(round_.base_run_ids) or await run_variant(
        round_, round_.base
    )
    base = result_of(base_reports)
    base_verdict = judge_variant(round_.base.variant_id, base, base, targets)
    verdicts = [base_verdict]
    run_ids = {round_.base.variant_id: [r.run_id for r in base_reports]}
    for variant in round_.variants:
        reports = await run_variant(round_, variant)
        verdict = judge_variant(variant.variant_id, result_of(reports), base, targets)
        verdicts.append(verdict)
        run_ids[variant.variant_id] = [report.run_id for report in reports]
        record_result(
            round_.round_id,
            variant.variant_id,
            run_ids[variant.variant_id],
            asdict(verdict),
        )
    winner = choose_winner(base_verdict, verdicts[1:])
    print(summarize(winner, round_.base.variant_id))
    return write_round_report(round_, verdicts, winner, run_ids)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(asyncio.run(run_round(load_round(args.round), load_targets())))
