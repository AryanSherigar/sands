"""Domain exceptions for indexing operations.

Messages carry no provider or user text to prevent log leakage.
"""

from app.exceptions.base import MemoryServiceError

HTTP_STATUS_SERVICE_UNAVAILABLE = 503
HTTP_STATUS_BAD_GATEWAY = 502


class EmbeddingNotConfiguredError(MemoryServiceError):
    def __init__(self, message: str = "Embedding API key not configured.") -> None:
        super().__init__(
            message=message,
            status_code=HTTP_STATUS_SERVICE_UNAVAILABLE,
            code="embedding_not_configured",
        )


class EmbeddingRateLimitedError(MemoryServiceError):
    def __init__(self, message: str = "Embedding service rate limited.") -> None:
        super().__init__(
            message=message,
            status_code=HTTP_STATUS_SERVICE_UNAVAILABLE,
            code="embedding_rate_limited",
        )


class EmbeddingTransientError(MemoryServiceError):
    def __init__(
        self, message: str = "Embedding service temporarily unavailable."
    ) -> None:
        super().__init__(
            message=message,
            status_code=HTTP_STATUS_SERVICE_UNAVAILABLE,
            code="embedding_transient",
        )


class EmbeddingPermanentError(MemoryServiceError):
    def __init__(self, message: str = "Embedding service error.") -> None:
        super().__init__(
            message=message,
            status_code=HTTP_STATUS_BAD_GATEWAY,
            code="embedding_permanent",
        )


class EmbeddingAnomalyError(MemoryServiceError):
    def __init__(
        self,
        message: str = "Embedding anomaly detected.",
        is_dimension_mismatch: bool = False,
    ) -> None:
        self.is_dimension_mismatch = is_dimension_mismatch
        super().__init__(
            message=message,
            status_code=HTTP_STATUS_BAD_GATEWAY,
            code="embedding_anomaly",
        )
