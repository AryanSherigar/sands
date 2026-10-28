"""Memory service integration exception classes."""

from app.exceptions.base import BaseAppException


class MemoryTemplateBuildError(BaseAppException):
    """Raised when the memory service rejects or fails a template build.

    The message is persisted to `Scenario.publish_error`, so it carries only
    memory's error code and HTTP status, never request or response text.
    """

    def __init__(self, code: str, upstream_status: int | None = None):
        self.code = code
        self.upstream_status = upstream_status
        status_suffix = f", status {upstream_status}" if upstream_status else ""
        super().__init__(
            message=f"Memory template build failed ({code}{status_suffix})",
            status_code=502,
        )


class MemoryPurgeError(BaseAppException):
    """Raised when the memory service fails a purge or a scope listing.

    Carries only memory's error code and HTTP status, never request or response
    text, so it is safe to log.
    """

    def __init__(self, code: str, upstream_status: int | None = None):
        self.code = code
        self.upstream_status = upstream_status
        status_suffix = f", status {upstream_status}" if upstream_status else ""
        super().__init__(
            message=f"Memory purge failed ({code}{status_suffix})",
            status_code=502,
        )
