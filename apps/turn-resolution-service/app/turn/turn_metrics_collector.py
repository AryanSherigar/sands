"""Collects one turn's operational metrics while the pipeline runs.

pipeline.py owns the collector and feeds it from what each step already
returns, so steps stay pure and never import this module. The collector only
accumulates; building the row never raises into the turn (see state_writer).
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

import structlog
from app.config import settings
from app.models.memory import MemoryContext
from app.models.tool_call import ToolCallLogEntry
from app.models.turn_metrics import CheckOutcome, TurnMetricsRecord

logger = structlog.get_logger()

EVENT_STAT_SNAPSHOT_TRUNCATED = "turn_metrics_stat_snapshot_truncated"
STEP_AI_ORCHESTRATOR = "ai_orchestrator"
STEP_REQUEST_RECEIVER = "request_receiver"
STEP_STATE_LOADER = "state_loader"
STEP_CONTEXT_RETRIEVAL = "context_retrieval"
STEP_CONDITION_EVALUATOR = "condition_evaluator"
STATE_SYSTEM_KEY_PREFIX = "_"
STATE_ENTITIES_KEY = "entities"
MS_PER_SECOND = 1000


@dataclass(frozen=True)
class IntakeMetrics:
    """What the pre-narration pass learned that the collector records."""

    fired_condition_ids: list[str] = field(default_factory=list)
    check_outcomes: list[CheckOutcome] = field(default_factory=list)
    condition_evaluator_ms: int | None = None


def to_milliseconds(seconds: float) -> int:
    return round(seconds * MS_PER_SECOND)


def numeric_snapshot(state: dict[str, object]) -> dict[str, float]:
    """Flatten the numeric leaves of the visible state tree into dotted paths,
    capped at the configured key count (extras are dropped and logged)."""
    flattened: dict[str, float] = {}
    _flatten_numbers(state, "", flattened)
    limit = settings.turn_metrics_stat_snapshot_max_keys
    if len(flattened) > limit:
        logger.info(EVENT_STAT_SNAPSHOT_TRUNCATED, dropped_keys=len(flattened) - limit)
    return dict(sorted(flattened.items())[:limit])


def _flatten_numbers(
    node: dict[str, object], prefix: str, found: dict[str, float]
) -> None:
    for key, value in node.items():
        if _is_skipped_key(key, prefix):
            continue
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            _flatten_numbers(value, f"{path}.", found)
            continue
        if _is_number(value):
            found[path] = float(value)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_skipped_key(key: str, prefix: str) -> bool:
    if prefix:
        return False
    return key.startswith(STATE_SYSTEM_KEY_PREFIX) or key == STATE_ENTITIES_KEY


class TurnMetricsCollector:
    def __init__(self, *, is_enabled: bool) -> None:
        self.is_enabled = is_enabled
        self._started_at = time.monotonic()
        self._generation_started_at: float | None = None
        self._first_token_ms: int | None = None
        self._generation_ms: int | None = None
        self._step_durations: dict[str, int] = {}
        self._memory_reasons: list[str] = []
        self._memory_retrieval_ms: int | None = None
        self._memory_facts_returned: int | None = None
        self._fired_condition_ids: list[str] = []
        self._check_outcomes: list[CheckOutcome] = []
        self._dropped_paths: list[str] = []
        self._dropped_count = 0

    @contextmanager
    def time_step(self, name: str) -> Iterator[None]:
        started_at = time.monotonic()
        try:
            yield
        finally:
            self.record_step_ms(name, to_milliseconds(time.monotonic() - started_at))

    def record_step_ms(self, name: str, milliseconds: int) -> None:
        self._step_durations[name] = milliseconds

    def start_generation(self) -> None:
        self._generation_started_at = time.monotonic()

    def mark_first_token(self) -> None:
        if self._first_token_ms is None:
            self._first_token_ms = to_milliseconds(time.monotonic() - self._started_at)

    def finish_generation(self) -> None:
        if self._generation_started_at is None:
            return
        elapsed = time.monotonic() - self._generation_started_at
        self._generation_ms = to_milliseconds(elapsed)
        self.record_step_ms(STEP_AI_ORCHESTRATOR, self._generation_ms)

    def record_memory(self, context: MemoryContext) -> None:
        self._memory_reasons = list(context.reasons)
        self._memory_retrieval_ms = context.retrieval_ms
        self._memory_facts_returned = len(context.items) if context.response else None
        if context.retrieval_ms is not None:
            self.record_step_ms(STEP_CONTEXT_RETRIEVAL, context.retrieval_ms)

    def record_intake(self, intake: IntakeMetrics) -> None:
        self._fired_condition_ids = list(intake.fired_condition_ids)
        self._check_outcomes = list(intake.check_outcomes)
        if intake.condition_evaluator_ms is not None:
            self.record_step_ms(STEP_CONDITION_EVALUATOR, intake.condition_evaluator_ms)

    def record_tool_calls(self, tool_calls: list[ToolCallLogEntry]) -> None:
        dropped = [call for call in tool_calls if not call.is_valid]
        self._dropped_count = len(dropped)
        self._dropped_paths = [
            str(call.arguments["path"])
            for call in dropped
            if isinstance(call.arguments.get("path"), str)
        ]

    def build_record(self, final_state: dict[str, object]) -> TurnMetricsRecord:
        return TurnMetricsRecord(
            first_token_ms=self._first_token_ms,
            generation_ms=self._generation_ms,
            total_ms=to_milliseconds(time.monotonic() - self._started_at),
            step_durations=dict(self._step_durations),
            memory_degraded_reasons=list(self._memory_reasons),
            memory_retrieval_ms=self._memory_retrieval_ms,
            memory_facts_returned=self._memory_facts_returned,
            fired_condition_ids=list(self._fired_condition_ids),
            dropped_mutation_count=self._dropped_count,
            dropped_mutation_paths=list(self._dropped_paths),
            check_outcomes=list(self._check_outcomes),
            stat_snapshot=numeric_snapshot(final_state),
        )
