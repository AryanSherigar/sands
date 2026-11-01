"""Wire contract of POST /v1/playthroughs/{playthrough_id}/memory/retry."""

from app.models.process_pending import ProcessPendingResponse
from app.models.retrieve import DegradedReason
from pydantic import BaseModel, Field


class RetryMemoryResponse(BaseModel):
    batches_reset: int
    failures_reset: int
    process_pending: ProcessPendingResponse
    degraded_reasons: list[DegradedReason] = Field(default_factory=list)
