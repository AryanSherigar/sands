"""Shared state and results of one extraction step inside a process-pending sweep."""

from dataclasses import dataclass, field
from uuid import UUID

from app.models.extraction import ExtractionCounts, ExtractionStepStatus


@dataclass
class RunState:
    counts: ExtractionCounts = field(default_factory=ExtractionCounts)
    stop_step: ExtractionStepStatus | None = None
    errors: list[str] = field(default_factory=list)
    touched_scopes: set[UUID] = field(default_factory=set)
    batches_seen: int = 0

    def stop(self, step: ExtractionStepStatus, error: str) -> None:
        if self.stop_step is None:
            self.stop_step = step
        if error not in self.errors:
            self.errors.append(error)

    def add_drops(self, dropped: dict[str, int]) -> None:
        for reason, count in dropped.items():
            current = self.counts.items_dropped.get(reason, 0)
            self.counts.items_dropped[reason] = current + count


@dataclass(frozen=True)
class ExtractionStepResult:
    step: ExtractionStepStatus
    counts: ExtractionCounts
    errors: list[str]
