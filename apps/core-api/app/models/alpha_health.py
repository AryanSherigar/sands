"""Shapes of the daily alpha health report. Counts and ids only, never text."""

from datetime import datetime

from pydantic import BaseModel


class RunCountsRow(BaseModel):
    label: str
    started: int
    completed: int
    abandoned: int
    silently_dropped: int


class TurnTotalsRow(BaseModel):
    turn_count: int
    turns_without_metrics: int
    prompt_tokens: int
    completion_tokens: int
    degraded_turns: int
    dropped_mutation_turns: int


class LatencyRow(BaseModel):
    first_token_p50_ms: float | None
    first_token_p95_ms: float | None
    total_p50_ms: float | None
    total_p95_ms: float | None


class FeedbackCountsRow(BaseModel):
    feedback: int
    flags: int
    surveys: int


class InviteSeatsRow(BaseModel):
    label: str
    seats_used: int
    max_seats: int
    is_revoked: bool


class CostEstimate(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    estimated_usd: float
    daily_budget_usd: float


class AlphaHealthReport(BaseModel):
    generated_at: datetime
    window_hours: int
    runs: list[RunCountsRow]
    endings: dict[str, int]
    completion_rate: float | None
    turns: TurnTotalsRow
    turns_without_metrics_ratio: float | None
    memory_degraded_rate: float | None
    dropped_mutation_rate: float | None
    latency: LatencyRow
    memory_degraded_by_reason: dict[str, int]
    retries_by_kind: dict[str, int]
    quota_trips: int
    cost: CostEstimate
    feedback: FeedbackCountsRow
    flagged_turn_ids: list[str]
    invites: list[InviteSeatsRow]
    breaches: list[str]
