"""Shared types of one process-pending sweep: context, mutable state, error codes."""

import time
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from app.config import Settings
from app.models.common import EmbeddingTargetKind, ScopeKind
from app.models.jobs import EmbeddingModelRow
from app.models.process_pending import EmbeddingStepStatus
from psycopg_pool import AsyncConnectionPool

ERROR_DIMENSION_MISMATCH = "embedding_dimension_mismatch"
ERROR_FALLBACK = "embedding_error"
STEP_RATE_LIMITED: EmbeddingStepStatus = "rate_limited"
STEP_ABORTED: EmbeddingStepStatus = "aborted"


class DocumentEmbedder(Protocol):
    async def embed_documents(
        self, texts: list[str], deadline_monotonic: float | None = None
    ) -> list[list[float]]: ...


@dataclass(frozen=True)
class EmbedTarget:
    kind: EmbeddingTargetKind
    target_id: UUID
    scope_kind: ScopeKind
    scope_id: UUID
    body: str


@dataclass(frozen=True)
class SweepContext:
    pool: AsyncConnectionPool
    settings: Settings
    embedder: DocumentEmbedder
    model: EmbeddingModelRow
    playthrough_id: UUID | None
    deadline_monotonic: float

    @property
    def is_unscoped(self) -> bool:
        return self.playthrough_id is None

    @property
    def is_deadline_passed(self) -> bool:
        return time.monotonic() >= self.deadline_monotonic


@dataclass
class SweepState:
    spans_embedded: int = 0
    facts_embedded: int = 0
    chars_embedded: int = 0
    batches_sent: int = 0
    targets_skipped: int = 0
    targets_claimed: int = 0
    is_cut_by_deadline: bool = False
    stop_step: EmbeddingStepStatus | None = None
    errors: list[str] = field(default_factory=list)
    failed_span_ids: set[UUID] = field(default_factory=set)
    failed_fact_ids: set[UUID] = field(default_factory=set)

    @property
    def is_stopped(self) -> bool:
        return self.stop_step is not None

    def request_stop(self, step: EmbeddingStepStatus, error_code: str) -> None:
        if self.stop_step is None or step == STEP_ABORTED:
            self.stop_step = step
        self.add_error(error_code)

    def add_error(self, error_code: str) -> None:
        if error_code not in self.errors:
            self.errors.append(error_code)

    def failed_ids(self, kind: EmbeddingTargetKind) -> set[UUID]:
        return self.failed_span_ids if kind == "span" else self.failed_fact_ids
