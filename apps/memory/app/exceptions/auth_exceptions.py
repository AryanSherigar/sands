"""Domain exceptions for service-to-service authentication."""

from app.exceptions.base import MemoryServiceError

HTTP_STATUS_UNAUTHORIZED = 401
HTTP_STATUS_FORBIDDEN = 403


class ServiceUnauthenticatedError(MemoryServiceError):
    def __init__(self) -> None:
        super().__init__(
            message="A bearer token is required",
            status_code=HTTP_STATUS_UNAUTHORIZED,
            code="unauthenticated",
        )


class ServiceTokenInvalidError(MemoryServiceError):
    def __init__(self) -> None:
        super().__init__(
            message="The bearer token is not valid for this service",
            status_code=HTTP_STATUS_UNAUTHORIZED,
            code="invalid_token",
        )


class ServiceCallerNotAllowedError(MemoryServiceError):
    def __init__(self) -> None:
        super().__init__(
            message="This caller is not allowed to use the memory service",
            status_code=HTTP_STATUS_FORBIDDEN,
            code="caller_not_allowed",
        )
