"""Domain exceptions for the schema migration runner."""

from app.exceptions.base import SimulationServiceError

HTTP_STATUS_INTERNAL_SERVER_ERROR = 500


class MigrationChecksumMismatchError(SimulationServiceError):
    def __init__(self, version: str) -> None:
        super().__init__(
            message=(
                f"Applied migration '{version}' no longer matches its recorded "
                "checksum; migrations are forward-only, add a new file instead."
            ),
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )


class MigrationFileMissingError(SimulationServiceError):
    def __init__(self, version: str) -> None:
        super().__init__(
            message=f"Applied migration '{version}' has no file on disk.",
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
        )
