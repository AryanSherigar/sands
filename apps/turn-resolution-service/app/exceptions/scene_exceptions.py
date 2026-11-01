"""Exceptions for strategy-mode scenes narrated here and owned by the simulation."""

from app.exceptions.base import BaseAppException

CODE_SCENE_NOT_FOUND = "scene_not_found"
CODE_SCENE_NOT_OPEN = "scene_not_open"
CODE_SCENE_TYPE_UNSUPPORTED = "scene_type_unsupported"
CODE_SCENE_KIND_MISMATCH = "scene_kind_mismatch"
CODE_SIMULATION_UNAVAILABLE = "simulation_unavailable"
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_UNPROCESSABLE = 422
HTTP_BAD_GATEWAY = 502


class SceneNotFoundError(BaseAppException):
    def __init__(self) -> None:
        super().__init__(
            message="Scene not found",
            status_code=HTTP_NOT_FOUND,
            error_code=CODE_SCENE_NOT_FOUND,
        )


class SceneNotOpenError(BaseAppException):
    def __init__(self) -> None:
        super().__init__(
            message="Scene is not open",
            status_code=HTTP_CONFLICT,
            error_code=CODE_SCENE_NOT_OPEN,
        )


class SceneTypeUnsupportedError(BaseAppException):
    def __init__(self) -> None:
        super().__init__(
            message="This scene type cannot be narrated yet",
            status_code=HTTP_UNPROCESSABLE,
            error_code=CODE_SCENE_TYPE_UNSUPPORTED,
        )


class SceneKindMismatchError(BaseAppException):
    def __init__(self) -> None:
        super().__init__(
            message="This message does not fit the scene",
            status_code=HTTP_UNPROCESSABLE,
            error_code=CODE_SCENE_KIND_MISMATCH,
        )


class SimulationUnavailableError(BaseAppException):
    """The simulation service did not answer or answered unusably.

    upstream_status is None when no HTTP response arrived. Never carries
    response text: scene exchanges contain the player's words.
    """

    def __init__(self, upstream_status: int | None = None) -> None:
        self.upstream_status = upstream_status
        super().__init__(
            message="Simulation service unavailable",
            status_code=HTTP_BAD_GATEWAY,
            error_code=CODE_SIMULATION_UNAVAILABLE,
        )
