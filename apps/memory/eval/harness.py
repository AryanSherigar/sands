"""CLI: `python -m eval.harness --corpus eval/corpus --campaigns C1,C2 --run-name baseline`."""

import argparse
import asyncio
import dataclasses
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings, get_settings

from eval.corpus_loader import Campaign, load_campaign
from eval.corpus_models import UNMEASURED_CLASSES
from eval.corpus_validate import validate_campaign, validate_class_minimums
from eval.credentials import resolve_api_key
from eval.driver import UsageTotals
from eval.errors import HarnessError
from eval.freeze import check_frozen
from eval.latency import latency_of
from eval.memory_http import MemoryHttp
from eval.prices import (
    DEFAULT_BUDGET_USD,
    PriceTable,
    RunUsage,
    assert_within_budget,
    compute_cost,
    load_prices,
)
from eval.report import format_markdown
from eval.run_models import ExtractionRecord, ProbeRecord, RunReport
from eval.runner import RunEnv, run_campaign
from eval.scoring.extraction import ExtractionObservation
from eval.stack import QUALITY_EMBED_TIMEOUT_SECONDS, Stack, start_stack, stop_stack
from eval.timing import parse_stage_timings

REPORTS_DIRECTORY = Path(__file__).parent / "reports"
VERSION_FILE = "VERSION"


def extraction_env(settings: Settings) -> dict[str, str]:
    """The extraction knobs of this run, handed to the scratch service unchanged."""
    env = {
        "EXTRACTION_MODEL_NAME": settings.extraction_model_name,
        "EXTRACTION_PROMPT_VERSION": settings.extraction_prompt_version,
        "EXTRACTION_BATCH_TURNS": str(settings.extraction_batch_turns),
    }
    if settings.extraction_thinking_level:
        env["EXTRACTION_THINKING_LEVEL"] = settings.extraction_thinking_level
    return env


def build_usage(
    totals: UsageTotals, query_characters: int, settings: Settings
) -> RunUsage:
    return RunUsage(
        extraction_model=settings.extraction_model_name,
        extraction_input_tokens=totals.extraction_input_tokens,
        extraction_output_tokens=totals.extraction_output_tokens,
        embedding_model=settings.embedding_model_name,
        characters_embedded=totals.characters_embedded,
        query_characters=query_characters,
    )


def make_guard(
    settings: Settings, prices: PriceTable | None, limit_usd: float
) -> Callable[[UsageTotals], None]:
    def guard(totals: UsageTotals) -> None:
        if prices is None:
            return
        cost = compute_cost(build_usage(totals, 0, settings), prices)
        assert_within_budget(cost, limit_usd)

    return guard


def load_and_validate(
    corpus_root: Path,
    campaign_ids: list[str],
    is_minimum_enforced: bool,
    is_freeze_enforced: bool = True,
) -> list[Campaign]:
    campaigns = [
        load_campaign(corpus_root / campaign_id) for campaign_id in campaign_ids
    ]
    errors = [error for campaign in campaigns for error in validate_campaign(campaign)]
    if is_minimum_enforced:
        errors += validate_class_minimums(campaigns)
    if errors:
        raise HarnessError("Corpus validation failed:\n" + "\n".join(errors))
    if is_freeze_enforced:
        check_frozen(corpus_root, campaigns)
    return campaigns


def assemble_report(
    run_id: str,
    campaigns: list[Campaign],
    corpus_root: Path,
    records: list[ProbeRecord],
    extractions: list[ExtractionRecord],
    usage: RunUsage,
    settings: Settings,
) -> RunReport:
    return RunReport(
        run_id=run_id,
        corpus_version=(corpus_root / VERSION_FILE).read_text(encoding="utf-8").strip(),
        content_hashes={c.campaign_id: c.content_hash for c in campaigns},
        pinned={
            "embedding_model": settings.embedding_model_name,
            "extraction_model": settings.extraction_model_name,
            "extraction_prompt_version": settings.extraction_prompt_version,
            "extraction_thinking_level": str(settings.extraction_thinking_level),
            "extraction_batch_turns": str(settings.extraction_batch_turns),
            "recent_window_turns": str(settings.recent_window_turns),
            "recall_budget_tokens": str(settings.recall_budget_tokens),
        },
        is_complete=True,
        probes=records,
        extraction=extractions,
        label_audit=label_audit_of(campaigns),
        latency=latency_of(records),
        usage=usage,
        unmeasured_classes=sorted(UNMEASURED_CLASSES),
    )


def label_audit_of(campaigns: list[Campaign]) -> dict[str, int]:
    total = sum(len(campaign.plants) for campaign in campaigns)
    return {"plants_total": total, "anchors_verified": total}


def write_report(report: RunReport) -> Path:
    REPORTS_DIRECTORY.mkdir(exist_ok=True)
    base = REPORTS_DIRECTORY / report.run_id
    if base.with_suffix(".json").exists():
        raise HarnessError(
            f"Report {report.run_id} already exists; reports are never overwritten"
        )
    base.with_suffix(".json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    base.with_suffix(".md").write_text(format_markdown(report), encoding="utf-8")
    return base.with_suffix(".json")


def write_observation(
    run_id: str, campaign_id: str, observation: ExtractionObservation
) -> None:
    path = REPORTS_DIRECTORY / f"{run_id}.{campaign_id}.observation.json"
    payload = dataclasses.asdict(observation)
    path.write_text(json.dumps(payload, default=sorted, indent=1), encoding="utf-8")


def write_observations(
    run_id: str, observations: dict[str, ExtractionObservation]
) -> None:
    REPORTS_DIRECTORY.mkdir(exist_ok=True)
    for campaign_id, observation in observations.items():
        write_observation(run_id, campaign_id, observation)


async def execute_campaigns(
    env: RunEnv, campaigns: list[Campaign]
) -> tuple[list[ProbeRecord], list[ExtractionRecord], dict[str, ExtractionObservation]]:
    records: list[ProbeRecord] = []
    extractions: list[ExtractionRecord] = []
    observations: dict[str, ExtractionObservation] = {}
    for campaign in campaigns:
        outcome = await run_campaign(env, campaign)
        records.extend(outcome.probes)
        extractions.append(outcome.extraction)
        observations[campaign.campaign_id] = outcome.observation
    return records, extractions, observations


@dataclass(frozen=True)
class RunParams:
    corpus_root: Path
    campaign_ids: list[str]
    run_name: str
    budget_usd: float
    is_priced: bool
    is_minimum_enforced: bool
    is_freeze_enforced: bool
    should_drop_db: bool
    env_overrides: dict[str, str] = field(default_factory=dict)


def settings_with(env_overrides: dict[str, str]) -> Settings:
    if not env_overrides:
        return get_settings()
    return Settings(**{name.lower(): value for name, value in env_overrides.items()})


async def _open_run(
    params: RunParams, settings: Settings, run_id: str, prices: PriceTable | None
) -> tuple[Stack, RunEnv]:
    guard = make_guard(settings, prices, params.budget_usd)
    stack = await start_stack(
        settings.memory_database_url,
        params.run_name,
        resolve_api_key(settings),
        QUALITY_EMBED_TIMEOUT_SECONDS,
        REPORTS_DIRECTORY / f"{run_id}.service.log",
        extraction={**extraction_env(settings), **params.env_overrides},
    )
    http = MemoryHttp(stack.base_url)
    return stack, RunEnv(
        http, stack.database_url, guard, settings.embedding_model_name, True
    )


def measurements_of(
    run_id: str,
    usage: RunUsage,
    prices: PriceTable | None,
    campaigns: list[Campaign],
    env_overrides: dict[str, str],
) -> dict[str, object]:
    log_path = REPORTS_DIRECTORY / f"{run_id}.service.log"
    timings = parse_stage_timings(log_path.read_text(encoding="utf-8").splitlines())
    return {
        "stage_ms": timings.retrieval_ms,
        "extraction_stage_ms": timings.extraction_ms,
        "cost_usd": compute_cost(usage, prices).total_usd if prices else None,
        "turn_count": sum(len(campaign.turns) for campaign in campaigns),
        "env_overrides": env_overrides,
    }


async def execute_run(params: RunParams) -> tuple[RunReport, Path]:
    settings = settings_with(params.env_overrides)
    campaigns = load_and_validate(
        params.corpus_root,
        params.campaign_ids,
        params.is_minimum_enforced,
        params.is_freeze_enforced,
    )
    run_id = f"{params.run_name}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}"
    prices = load_prices() if params.is_priced else None
    stack, env = await _open_run(params, settings, run_id, prices)
    try:
        records, extractions, observations = await execute_campaigns(env, campaigns)
    finally:
        await env.http.close()
        await stop_stack(stack, settings.memory_database_url, params.should_drop_db)
    usage = build_usage(env.usage, env.query_characters, settings)
    write_observations(run_id, observations)
    report = assemble_report(
        run_id, campaigns, params.corpus_root, records, extractions, usage, settings
    )
    extra = measurements_of(run_id, usage, prices, campaigns, params.env_overrides)
    report = report.model_copy(update=extra)
    return report, write_report(report)


def params_from_args(args: argparse.Namespace) -> RunParams:
    return RunParams(
        corpus_root=Path(args.corpus),
        campaign_ids=args.campaigns.split(","),
        run_name=args.run_name,
        budget_usd=args.budget,
        is_priced=not args.allow_unpriced,
        is_minimum_enforced=not args.no_minimums,
        is_freeze_enforced=not args.allow_unfrozen,
        should_drop_db=args.drop_db,
    )


async def run(args: argparse.Namespace) -> Path:
    _, path = await execute_run(params_from_args(args))
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="eval/corpus")
    parser.add_argument("--campaigns", default="C1,C2")
    parser.add_argument("--run-name", default="baseline")
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD)
    parser.add_argument("--allow-unpriced", action="store_true")
    parser.add_argument("--no-minimums", action="store_true")
    parser.add_argument("--allow-unfrozen", action="store_true")
    parser.add_argument("--drop-db", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    print(asyncio.run(run(parse_args())))
