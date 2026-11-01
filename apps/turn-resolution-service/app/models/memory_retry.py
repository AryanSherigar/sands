"""Result shapes for the player-facing "Retry memory" action."""

from pydantic import BaseModel, Field


class MemoryRetryResult(BaseModel):
    """Subset of memory's retry response that TRS reads; unknown fields are ignored."""

    batches_reset: int = 0
    failures_reset: int = 0
    degraded_reasons: list[str] = Field(default_factory=list)


class MemoryRetryResponse(BaseModel):
    """What the frontend receives: the reasons still holding after the retry."""

    degraded_reasons: list[str] = Field(default_factory=list)
