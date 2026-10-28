from app.exceptions.base import SimulationServiceError

HTTP_STATUS_INTERNAL_SERVER_ERROR = 500


class InvalidSceneTransitionError(SimulationServiceError):
    def __init__(self, status: str) -> None:
        super().__init__(
            message=f"A scene cannot be resolved into status '{status}'.",
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )


class InvalidScenePackageError(SimulationServiceError):
    def __init__(self, reasons: list[str]) -> None:
        super().__init__(
            message=f"A scene package is invalid: {'; '.join(reasons)}",
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )
