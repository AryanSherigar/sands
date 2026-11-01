"""Exceptions for delivering turns to the greenfield memory service."""

from app.exceptions.base import BaseAppException

CODE_UNAVAILABLE = "unavailable"
CODE_INVALID_RESPONSE = "invalid_response"
CODE_UNKNOWN = "unknown"
CODE_INVALID_PAYLOAD = "invalid_payload"
CODE_TURN_LOG_MISSING = "turn_log_missing"
CODE_PARTICIPANT_MISSING = "participant_missing"
CODE_NOT_REGISTERED = "not_registered"


class MemoryIngestError(BaseAppException):
    """Memory did not accept an ingest request.

    upstream_status is None when no HTTP response arrived (timeout, refused).
    code is memory's stable error code or one of this module's CODE_* values,
    never response text.
    """

    def __init__(self, code: str, upstream_status: int | None = None):
        self.code = code
        self.upstream_status = upstream_status
        super().__init__(message=f"Memory ingest failed: {code}", status_code=502)


class MemoryRetrieveError(BaseAppException):
    """Memory did not answer a retrieve request.

    upstream_status is None when no HTTP response arrived (timeout, refused).
    code is memory's stable error code or one of this module's CODE_* values,
    never response text: the request carries the player's action.
    """

    def __init__(self, code: str, upstream_status: int | None = None):
        self.code = code
        self.upstream_status = upstream_status
        super().__init__(message=f"Memory retrieve failed: {code}", status_code=502)

    @property
    def is_not_registered(self) -> bool:
        return self.code == CODE_NOT_REGISTERED


class InternalEndpointDisabledError(BaseAppException):
    """Raised when an internal endpoint is called but no service token is set."""

    def __init__(self, message: str = "Internal endpoint is disabled"):
        super().__init__(message=message, status_code=503)


class InvalidInternalTokenError(BaseAppException):
    """Raised when an internal endpoint is called with a missing or wrong token."""

    def __init__(self, message: str = "Invalid internal service token"):
        super().__init__(message=message, status_code=401)


class InvalidOutboxPayloadError(BaseAppException):
    """Raised when a stored outbox row cannot be turned into a valid ingest item."""

    def __init__(self, message: str = "Outbox payload is invalid"):
        super().__init__(message=message, status_code=500)


class MemoryRetryError(BaseAppException):
    """Memory could not run a retry pass.

    code is memory's stable error code or one of this module's CODE_* values,
    never response text.
    """

    def __init__(self, code: str, upstream_status: int | None = None):
        self.code = code
        self.upstream_status = upstream_status
        super().__init__(message=f"Memory retry failed: {code}", status_code=502)
