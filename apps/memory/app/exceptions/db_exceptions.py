"""Domain exceptions for database access.

health_repo returns booleans instead of raising these, since GET /health reports
a structured status body rather than the generic error_handler response shape.
"""

from app.exceptions.base import MemoryServiceError

HTTP_STATUS_SERVICE_UNAVAILABLE = 503


class DatabaseUnavailableError(MemoryServiceError):
    def __init__(self, message: str = "Database is unreachable.") -> None:
        super().__init__(message=message, status_code=HTTP_STATUS_SERVICE_UNAVAILABLE)


class RequiredExtensionMissingError(MemoryServiceError):
    def __init__(self, extension_name: str) -> None:
        super().__init__(
            message=f"Required Postgres extension '{extension_name}' is not installed.",
            status_code=HTTP_STATUS_SERVICE_UNAVAILABLE,
        )
