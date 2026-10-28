from app.exceptions.base import SimulationServiceError

HTTP_STATUS_NOT_FOUND = 404


class PlaythroughNotFoundError(SimulationServiceError):
    """Raised for an unknown playthrough and for one owned by someone else, identically."""

    def __init__(self) -> None:
        super().__init__(
            message="Playthrough not found.", status_code=HTTP_STATUS_NOT_FOUND
        )
