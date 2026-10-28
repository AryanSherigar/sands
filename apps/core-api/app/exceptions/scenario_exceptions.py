"""Scenario domain exception classes."""

from app.exceptions.base import BaseAppException


class ScenarioNotFoundError(BaseAppException):
    """Raised when a scenario is not found or inaccessible."""

    def __init__(self, message: str = "Scenario not found"):
        super().__init__(message=message, status_code=404)


class ScenarioAccessDeniedError(BaseAppException):
    """Raised when a user is not permitted to access or modify a scenario."""

    def __init__(self, message: str = "Access denied for this scenario"):
        super().__init__(message=message, status_code=403)


class ScenarioValidationError(BaseAppException):
    """Raised when scenario fields or rules fail domain validation."""

    def __init__(self, message: str = "Invalid scenario configuration"):
        super().__init__(message=message, status_code=400)


class ScenarioAlreadyPublishingError(BaseAppException):
    """Raised when publish or edit is attempted while a publish is in flight."""

    def __init__(self, message: str = "Scenario is currently being published"):
        super().__init__(message=message, status_code=409)


class PrivateScenarioShareError(BaseAppException):
    """Raised when a share link is requested for a private scenario's playthrough."""

    def __init__(
        self, message: str = "Playthroughs of a private scenario cannot be shared"
    ):
        super().__init__(message=message, status_code=403)


class ScenarioModeLockedError(BaseAppException):
    """Raised when a strategy scenario is switched to another mode."""

    def __init__(
        self, message: str = "A strategy scenario cannot be switched to another mode"
    ):
        super().__init__(message=message, status_code=422)


class ScenarioEditConflictError(BaseAppException):
    """Raised when a write was made against a copy of the story that has since
    changed in another window."""

    def __init__(
        self,
        message: str = "This story changed in another window. Reload to see the latest.",
    ):
        super().__init__(
            message=message, status_code=409, error_code="scenario_edit_conflict"
        )


class InviteInvalidError(BaseAppException):
    """Raised when an invite link is unknown (404) or already used or expired (410)."""

    def __init__(
        self, message: str = "Invite not found", status_code: int = 404
    ) -> None:
        super().__init__(message=message, status_code=status_code)
