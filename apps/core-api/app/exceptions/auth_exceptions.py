from app.exceptions.base import BaseAppException


class AuthError(BaseAppException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class InvalidTokenError(AuthError):
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message)


class InternalEndpointDisabledError(BaseAppException):
    def __init__(self, message: str = "Internal endpoint is disabled"):
        super().__init__(
            message, status_code=503, error_code="internal_endpoint_disabled"
        )


class InvalidInternalTokenError(BaseAppException):
    def __init__(self, message: str = "Invalid internal service token"):
        super().__init__(message, status_code=401, error_code="invalid_internal_token")
