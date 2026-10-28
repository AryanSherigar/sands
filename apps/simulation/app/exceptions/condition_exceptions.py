from app.exceptions.base import SimulationServiceError


class UnsupportedMetricError(SimulationServiceError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500, code="unsupported_metric")


class UnsupportedEffectError(SimulationServiceError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500, code="unsupported_effect")
