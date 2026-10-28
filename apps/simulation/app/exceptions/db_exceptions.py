"""Domain exceptions for database access.

health_repo returns booleans instead of raising these, since GET /health reports
a structured status body rather than the generic error_handler response shape.
"""

from app.exceptions.base import SimulationServiceError

HTTP_STATUS_SERVICE_UNAVAILABLE = 503


class DatabaseUnavailableError(SimulationServiceError):
    def __init__(self, message: str = "Database is unreachable.") -> None:
        super().__init__(message=message, status_code=HTTP_STATUS_SERVICE_UNAVAILABLE)
