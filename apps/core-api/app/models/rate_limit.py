"""Response body for 429/503 rate-limit and quota errors."""

from datetime import datetime

from pydantic import BaseModel


class RateLimitErrorResponse(BaseModel):
    detail: str
    code: str
    scope: str
    reset_at: datetime | None = None
