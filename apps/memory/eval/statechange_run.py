"""CLI: `python -m eval.statechange_run --label v3 --env EXTRACTION_PROMPT_VERSION=extraction_v3`.

Runs every state-change case through the real extraction pipeline (live model) on a
scratch database, in this process: no HTTP service, no embeddings, no retrieval."""

import argparse
import asyncio
import json
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.config import Settings, get_settings
from app.integrations.extraction_client import build_extraction_client
from app.integrations.extraction_queue import ExtractionQueue
from app.models.extraction import ValidatedPlan
from app.repositories import extraction_batch_repo
from app.services.extraction_service import ExtractionService
from app.services.retrieval_service import RetrievalService
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from eval.credentials import resolve_api_key
from eval.errors import BudgetExceededError, HarnessError
from eval.prices import RunUsage, compute_cost, load_prices
from eval.scoring.statechange import (
    CaseOutcome,
    CaseScore,
    ObservedText,
    score_case,
    summarize_by_category,
)
from eval.stack import Stack, prepare_scratch_database, stop_stack
from eval.statechange_cases import StateChangeCase, load_cases
from eval.statechange_seed import SeededCase, seed_case

REPORTS_DIRECTORY = Path(__file__).parent / "reports"
DEADLINE_SECONDS = 120
DEFAULT_REPEATS = 3
DEFAULT_BUDGET_USD = 1.0
SELECT_SUPERSEDED = "SELECT fact_id FROM memory_supersession WHERE playthrough_id = %s"
SELECT_ENTITY_NAMES = (
    "SELECT entity_id, canonical_name FROM memory_entity WHERE scope_id IN "
    "(SELECT template_id FROM memory_playthrough WHERE playthrough_id = %s) "
    "OR scope_id = %s"
)
TRUNCATE_QUEUE = (
    "TRUNCATE procrastinate_jobs, procrastinate_events, "
    "procrastinate_periodic_defers, procrastinate_workers RESTART IDENTITY CASCADE"
)
EMBEDDING_MODEL = "text-embedding-005"
APPLIED = "applied"


def parse_env(pairs: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for pair in pairs:
        name, separator, value = pair.partition("=")
        if not separator:
            raise HarnessError(f"--env expects NAME=VALUE, got {pair!r}")
        env[name.strip().lower()] = value
    return env


def build_settings(api_key: str, env: dict[str, str]) -> Settings:
    base: dict[str, object] = {"_env_file": None, "extraction_api_key": api_key}
    return Settings(**{**base, **env})  # type: ignore[arg-type]


def _object_text(
    object_ref: str | None, literal: str | None, names: dict[str, str]
) -> str:
    if literal:
        return literal
    return names.get(object_ref or "", "")


def observe_plan(
    plan: ValidatedPlan, seeded: SeededCase, names: dict[str, str]
) -> list[ObservedText]:
    key_of = {str(entity_id): key for key, entity_id in seeded.entity_ids.items()}
    temp_names = {entity.temp_key: entity.name for entity in plan.new_entities}
    observed: list[ObservedText] = []
    for fact in plan.facts:
        subject = plan.reused_entities.get(fact.subject, fact.subject)
        object_ref = plan.reused_entities.get(fact.object or "", fact.object)
        known = {**names, **temp_names}
        object_text = _object_text(object_ref, fact.object_literal, known)
        claim = (
            f"{known.get(subject, '')} {fact.predicate.replace('_', ' ')} {object_text}"
        )
        observed.append(
            ObservedText(key_of.get(subject), fact.predicate, claim, fact.assertion)
        )
    return observed


async def _entity_names(
    connection: AsyncConnection, seeded: SeededCase
) -> dict[str, str]:
    cursor = await connection.execute(
        SELECT_ENTITY_NAMES, (seeded.playthrough_id, seeded.playthrough_id)
    )
    return {str(row[0]): row[1] for row in await cursor.fetchall()}


async def _retired_keys(
    connection: AsyncConnection, seeded: SeededCase
) -> frozenset[str]:
    cursor = await connection.execute(SELECT_SUPERSEDED, (seeded.playthrough_id,))
    retired = {row[0] for row in await cursor.fetchall()}
    return frozenset(
        key for key, fact_id in seeded.fact_ids.items() if fact_id in retired
    )


async def _applied_plans(
    connection: AsyncConnection, playthrough_id: UUID
) -> list[ValidatedPlan]:
    batches = await extraction_batch_repo.list_batches(
        connection, "playthrough", playthrough_id, [APPLIED]
    )
    return [
        ValidatedPlan.model_validate(batch.validated_plan)
        for batch in batches
        if batch.validated_plan
    ]


async def collect_outcome(
    pool: AsyncConnectionPool, seeded: SeededCase, input_tokens: int, output_tokens: int
) -> CaseOutcome:
    async with pool.connection() as connection:
        plans = await _applied_plans(connection, seeded.playthrough_id)
        names = await _entity_names(connection, seeded)
        retired = await _retired_keys(connection, seeded)
    facts = [item for plan in plans for item in observe_plan(plan, seeded, names)]
    return CaseOutcome(retired, facts, input_tokens, output_tokens, bool(plans))


async def run_case(
    pool: AsyncConnectionPool, service: ExtractionService, case: StateChangeCase
) -> CaseScore:
    async with pool.connection() as connection:
        seeded = await seed_case(connection, case)
    result = await service.process(
        seeded.playthrough_id, time.monotonic() + DEADLINE_SECONDS
    )
    counts = result.counts
    outcome = await collect_outcome(
        pool, seeded, counts.input_tokens, counts.output_tokens
    )
    return score_case(case, outcome)


def cost_of(scores: list[CaseScore], model: str) -> float:
    usage = RunUsage(
        extraction_model=model,
        extraction_input_tokens=sum(s.input_tokens for s in scores),
        extraction_output_tokens=sum(s.output_tokens for s in scores),
        embedding_model=EMBEDDING_MODEL,
    )
    return compute_cost(usage, load_prices()).total_usd


async def run_repeat(
    pool: AsyncConnectionPool, service: ExtractionService, cases: list[StateChangeCase]
) -> list[CaseScore]:
    return [await run_case(pool, service, case) for case in cases]


def build_service(
    pool: AsyncConnectionPool, settings: Settings, queue: ExtractionQueue
) -> ExtractionService:
    return ExtractionService(
        pool,
        settings,
        build_extraction_client(settings),
        queue,
        RetrievalService(pool, settings, None),
    )


async def _drive(
    pool: AsyncConnectionPool,
    settings: Settings,
    cases: list[StateChangeCase],
    repeats: int,
    budget_usd: float,
) -> list[list[CaseScore]]:
    async with pool.connection() as connection:
        await connection.execute(TRUNCATE_QUEUE)
    queue = ExtractionQueue(settings.extraction_worker_count, 1)
    await queue.open(pool)
    service = build_service(pool, settings, queue)
    repeat_scores: list[list[CaseScore]] = []
    try:
        for _ in range(repeats):
            repeat_scores.append(await run_repeat(pool, service, cases))
            spent = cost_of(
                [s for scores in repeat_scores for s in scores],
                settings.extraction_model_name,
            )
            if spent > budget_usd:
                raise BudgetExceededError(f"Spent ${spent:.4f}, limit ${budget_usd}")
    finally:
        await queue.close()
    return repeat_scores


async def run_variant(
    settings: Settings,
    api_key: str,
    cases: list[StateChangeCase],
    repeats: int,
    budget_usd: float,
) -> list[list[CaseScore]]:
    name, url = await prepare_scratch_database(
        settings.memory_database_url, "statechange", api_key
    )
    try:
        async with AsyncConnectionPool(url, min_size=1, max_size=4, open=False) as pool:
            return await _drive(pool, settings, cases, repeats, budget_usd)
    finally:
        await stop_stack(Stack(name, url, ""), settings.memory_database_url, True)


def build_report(
    label: str,
    env: dict[str, str],
    settings: Settings,
    repeat_scores: list[list[CaseScore]],
) -> dict[str, object]:
    every_score = [score for scores in repeat_scores for score in scores]
    per_repeat = [
        {name: asdict(summary) for name, summary in summarize_by_category(s).items()}
        for s in repeat_scores
    ]
    return {
        "label": label,
        "created_at": datetime.now(UTC).isoformat(),
        "env": env,
        "model": settings.extraction_model_name,
        "repeats": len(repeat_scores),
        "cost_usd": cost_of(every_score, settings.extraction_model_name),
        "case_runs": len(every_score),
        "pooled": {
            name: asdict(summary)
            for name, summary in summarize_by_category(every_score).items()
        },
        "per_repeat": per_repeat,
        "case_scores": [asdict(score) for score in every_score],
    }


def format_table(report: dict[str, object]) -> str:
    lines = [
        f"{report['label']}: cost ${report['cost_usd']:.4f}, repeats {report['repeats']}"
    ]
    lines.append(
        "category          sup_recall  false_sup  req_recall  leaks  negated  unapplied"
    )
    pooled: dict[str, dict[str, object]] = report["pooled"]  # type: ignore[assignment]
    for name, row in pooled.items():
        lines.append(
            f"{name:<17} {_pct(row['supersession_recall']):>10}  "
            f"{_pct(row['false_supersession_rate']):>9}  {_pct(row['required_recall']):>10}  "
            f"{row['leaks']:>5}  {row['negated']:>7}  {row['unapplied_cases']:>9}"
        )
    return "\n".join(lines)


def _pct(value: object) -> str:
    return "-" if value is None else f"{float(value):.2f}"  # type: ignore[arg-type]


def select_cases(
    cases: list[StateChangeCase], only: list[str]
) -> list[StateChangeCase]:
    if not only:
        return cases
    chosen = [case for case in cases if case.case_id in only]
    if len(chosen) != len(set(only)):
        raise HarnessError("--only names a case that does not exist")
    return chosen


async def main(args: argparse.Namespace) -> None:
    env = parse_env(args.env)
    api_key = resolve_api_key(get_settings())
    settings = build_settings(api_key, env)
    cases = select_cases(load_cases(Path(args.cases)), args.only)
    repeat_scores = await run_variant(
        settings, api_key, cases, args.repeats, args.budget
    )
    report = build_report(args.label, env, settings, repeat_scores)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = REPORTS_DIRECTORY / f"statechange-{args.label}-{stamp}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(format_table(report))
    print(f"report: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--env", action="append", default=[])
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD)
    parser.add_argument(
        "--cases", default=str(Path(__file__).parent / "statechange" / "cases.jsonl")
    )
    parser.add_argument("--only", action="append", default=[])
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
