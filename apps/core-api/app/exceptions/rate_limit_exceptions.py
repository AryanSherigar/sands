"""Rate-limit and quota domain exceptions."""

from dataclasses import dataclass
from datetime import datetime

from app.exceptions.base import BaseAppException

CODE_RATE_LIMITED = "rate_limited"
CODE_QUOTA_EXCEEDED = "quota_exceeded"
CODE_FEATURE_UNAVAILABLE = "feature_unavailable"
CODE_QUOTA_UNAVAILABLE = "quota_unavailable"


@dataclass(frozen=True)
class LimitPolicy:
    """The limit a 429 refers to, rendered into RateLimit-Policy/RateLimit headers."""

    limit: int
    window_seconds: int
    remaining: int = 0


class RateLimitExceededError(BaseAppException):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        scope: str,
        reset_at: datetime | None,
        retry_after_seconds: int | None,
        policy: LimitPolicy | None = None,
    ) -> None:
        super().__init__(message=message, status_code=429)
        self.code = code
        self.scope = scope
        self.reset_at = reset_at
        self.retry_after_seconds = retry_after_seconds
        self.policy = policy


class QuotaStoreUnavailableError(BaseAppException):
    """The counter store failed, so an AI-cost operation is refused (fail closed)."""

    def __init__(self, scope: str) -> None:
        super().__init__(
            message="This feature is temporarily unavailable. Please try again shortly.",
            status_code=503,
        )
        self.code = CODE_QUOTA_UNAVAILABLE
        self.scope = scope
