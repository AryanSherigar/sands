"""Simulation service integration exception classes."""

from app.exceptions.base import BaseAppException


class SimulationUnavailableError(BaseAppException):
    """Raised when the simulation service cannot be reached or fails; retryable."""

    def __init__(self, upstream_status: int | None = None):
        self.upstream_status = upstream_status
        super().__init__(
            message="The campaign world is not ready yet. Try again shortly.",
            status_code=503,
            error_code="simulation_unavailable",
        )


class SimulationRejectedError(BaseAppException):
    """Raised when the simulation service refuses to initialize the campaign."""

    def __init__(self, code: str, upstream_status: int):
        self.code = code
        self.upstream_status = upstream_status
        super().__init__(
            message=f"The campaign could not be started ({code}).",
            status_code=422,
            error_code="simulation_rejected",
        )
