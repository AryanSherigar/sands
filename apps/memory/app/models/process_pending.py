"""Wire contract of POST /v1/jobs/process-pending."""

from typing import Literal
from uuid import UUID

from app.models.extraction import ExtractionCounts, ExtractionStepStatus
from pydantic import BaseModel, Field

EmbeddingStepStatus = Literal[
    "idle", "completed", "deadline_reached", "rate_limited", "aborted", "unconfigured"
]


class ProcessPendingRequest(BaseModel):
    playthrough_id: UUID | None = None
    deadline_seconds: int | None = Field(default=None, ge=1)


class ProcessPendingCounts(BaseModel):
    spans_embedded: int = 0
    facts_embedded: int = 0
    characters_embedded: int = 0
    tokens_estimated: int = 0
    batches_sent: int = 0
    targets_skipped: int = 0
    playthroughs_advanced: int = 0
    model_flipped: bool = False
    old_vectors_deleted: int = 0
    templates_gc_deleted: int = 0
    templates_gc_retained: int = 0


class ProcessPendingResponse(BaseModel):
    embedding_step: EmbeddingStepStatus
    counts: ProcessPendingCounts
    errors: list[str] = Field(default_factory=list)
    extraction_step: ExtractionStepStatus = "idle"
    extraction_counts: ExtractionCounts = Field(default_factory=ExtractionCounts)
