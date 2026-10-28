from app.exceptions.base import SimulationServiceError

HTTP_STATUS_UNAUTHORIZED = 401
HTTP_STATUS_SERVICE_UNAVAILABLE = 503


class AuthError(SimulationServiceError):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message=message, status_code=HTTP_STATUS_UNAUTHORIZED)


class InvalidTokenError(AuthError):
    def __init__(self, message: str = "Invalid token") -> None:
        super().__init__(message)


class InternalEndpointDisabledError(SimulationServiceError):
    """Raised when an internal endpoint is called but no service token is set."""

    def __init__(self, message: str = "Internal endpoint is disabled") -> None:
        super().__init__(message=message, status_code=HTTP_STATUS_SERVICE_UNAVAILABLE)


class InvalidInternalTokenError(SimulationServiceError):
    def __init__(self, message: str = "Invalid internal service token") -> None:
        super().__init__(message=message, status_code=HTTP_STATUS_UNAUTHORIZED)
