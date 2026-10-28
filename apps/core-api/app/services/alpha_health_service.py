import uuid
from datetime import datetime, timedelta

import structlog
from app.config import settings
from app.models.alpha_health import (
    AlphaHealthReport,
    CostEstimate,
    RunCountsRow,
    TurnTotalsRow,
)
from app.repositories.alpha_health_repo import AlphaHealthRepo

logger = structlog.get_logger()

EVENT_ALPHA_HEALTH_THRESHOLD_BREACHED = "alpha_health_threshold_breached"
METRIC_TURNS_WITHOUT_METRICS = "turns_without_metrics_ratio"
METRIC_MEMORY_DEGRADED = "memory_degraded_rate"
METRIC_ESTIMATED_SPEND = "estimated_spend"
METRIC_COMPLETION_RATE = "completion_rate"
EVENT_NAME_QUOTA_EXCEEDED = "quota_exceeded"
TOKENS_PER_MILLION = 1_000_000


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _estimate_cost(totals: TurnTotalsRow) -> CostEstimate:
    estimated = (
        totals.prompt_tokens * settings.alpha_prompt_usd_per_million_tokens
        + totals.completion_tokens * settings.alpha_completion_usd_per_million_tokens
    ) / TOKENS_PER_MILLION
    return CostEstimate(
        prompt_tokens=totals.prompt_tokens,
        completion_tokens=totals.completion_tokens,
        estimated_usd=round(estimated, 4),
        daily_budget_usd=settings.alpha_daily_budget_usd,
    )


def _completion_rate(runs: list[RunCountsRow]) -> float | None:
    return _ratio(sum(run.completed for run in runs), sum(run.started for run in runs))


def _find_breaches(
    without_metrics: float | None,
    degraded: float | None,
    cost: CostEstimate,
    completion: float | None,
) -> list[str]:
    breaches: list[str] = []
    if (
        without_metrics is not None
        and without_metrics > settings.alpha_max_turns_without_metrics_ratio
    ):
        breaches.append(METRIC_TURNS_WITHOUT_METRICS)
    if degraded is not None and degraded > settings.alpha_max_memory_degraded_rate:
        breaches.append(METRIC_MEMORY_DEGRADED)
    spend_limit = cost.daily_budget_usd * settings.alpha_spend_alert_fraction
    if cost.daily_budget_usd > 0 and cost.estimated_usd > spend_limit:
        breaches.append(METRIC_ESTIMATED_SPEND)
    is_completion_floor_set = settings.alpha_min_completion_rate > 0
    if (
        is_completion_floor_set
        and completion is not None
        and completion < settings.alpha_min_completion_rate
    ):
        breaches.append(METRIC_COMPLETION_RATE)
    return breaches


class AlphaHealthService:
    def __init__(self, repo: AlphaHealthRepo) -> None:
        self._repo = repo

    async def build_report(self, now: datetime) -> AlphaHealthReport:
        user_ids = await self._repo.list_tester_user_ids()
        since = now - timedelta(hours=settings.alpha_health_window_hours)
        stale_before = now - timedelta(hours=settings.alpha_stale_run_hours)
        runs = await self._repo.list_run_counts(user_ids, stale_before)
        totals = await self._repo.get_turn_totals(user_ids, since)
        report = await self._assemble(now, user_ids, since, runs, totals)
        report.breaches = _find_breaches(
            report.turns_without_metrics_ratio,
            report.memory_degraded_rate,
            report.cost,
            report.completion_rate,
        )
        self._log_breaches(report.breaches)
        return report

    async def _assemble(
        self,
        now: datetime,
        user_ids: list[uuid.UUID],
        since: datetime,
        runs: list[RunCountsRow],
        totals: TurnTotalsRow,
    ) -> AlphaHealthReport:
        return AlphaHealthReport(
            generated_at=now,
            window_hours=settings.alpha_health_window_hours,
            runs=runs,
            endings=await self._repo.count_endings(user_ids),
            completion_rate=_completion_rate(runs),
            turns=totals,
            turns_without_metrics_ratio=_ratio(
                totals.turns_without_metrics, totals.turn_count
            ),
            memory_degraded_rate=_ratio(totals.degraded_turns, totals.turn_count),
            dropped_mutation_rate=_ratio(
                totals.dropped_mutation_turns, totals.turn_count
            ),
            latency=await self._repo.get_latency(user_ids, since),
            memory_degraded_by_reason=await self._repo.count_degraded_reasons(
                user_ids, since
            ),
            retries_by_kind=await self._repo.count_retries_by_kind(user_ids, since),
            quota_trips=await self._repo.count_events(
                user_ids, since, EVENT_NAME_QUOTA_EXCEEDED
            ),
            cost=_estimate_cost(totals),
            feedback=await self._repo.get_feedback_counts(user_ids, since),
            flagged_turn_ids=await self._flagged_turn_ids(user_ids, since),
            invites=await self._repo.list_invite_seats(),
            breaches=[],
        )

    async def _flagged_turn_ids(
        self, user_ids: list[uuid.UUID], since: datetime
    ) -> list[str]:
        turn_ids = await self._repo.list_flagged_turn_ids(user_ids, since)
        return [str(turn_id) for turn_id in turn_ids]

    @staticmethod
    def _log_breaches(breaches: list[str]) -> None:
        for metric in breaches:
            logger.error(EVENT_ALPHA_HEALTH_THRESHOLD_BREACHED, metric=metric)
