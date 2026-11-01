"""Domain exceptions for extraction operations.

Messages carry no provider, prompt or model-output text to prevent log leakage.
"""

from app.exceptions.base import MemoryServiceError

HTTP_STATUS_SERVICE_UNAVAILABLE = 503
HTTP_STATUS_BAD_GATEWAY = 502


class ExtractionNotConfiguredError(MemoryServiceError):
    def __init__(self, message: str = "Extraction API key not configured.") -> None:
        super().__init__(
            message=message,
            status_code=HTTP_STATUS_SERVICE_UNAVAILABLE,
            code="extraction_not_configured",
        )


class ExtractionRateLimitedError(MemoryServiceError):
    def __init__(self, message: str = "Extraction service rate limited.") -> None:
        super().__init__(
            message=message,
            status_code=HTTP_STATUS_SERVICE_UNAVAILABLE,
            code="extraction_rate_limited",
        )


class ExtractionTransientError(MemoryServiceError):
    def __init__(
        self, message: str = "Extraction service temporarily unavailable."
    ) -> None:
        super().__init__(
            message=message,
            status_code=HTTP_STATUS_SERVICE_UNAVAILABLE,
            code="extraction_transient",
        )


class ExtractionPermanentError(MemoryServiceError):
    def __init__(self, message: str = "Extraction service error.") -> None:
        super().__init__(
            message=message,
            status_code=HTTP_STATUS_BAD_GATEWAY,
            code="extraction_permanent",
        )


class ExtractionConfigError(MemoryServiceError):
    def __init__(
        self, message: str = "Extraction request configuration rejected."
    ) -> None:
        super().__init__(
            message=message,
            status_code=HTTP_STATUS_BAD_GATEWAY,
            code="extraction_config_rejected",
        )


class ExtractionInvalidOutputError(MemoryServiceError):
    def __init__(self, message: str = "Extraction output failed validation.") -> None:
        super().__init__(
            message=message,
            status_code=HTTP_STATUS_BAD_GATEWAY,
            code="extraction_invalid_output",
        )
