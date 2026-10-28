"""Playthrough domain exception classes."""

from app.exceptions.base import BaseAppException


class PlaythroughNotFoundError(BaseAppException):
    """Raised when a playthrough is not found."""

    def __init__(self, message: str = "Playthrough not found"):
        super().__init__(message=message, status_code=404)


class PlaythroughAccessDeniedError(BaseAppException):
    """Raised when a user is not a participant of the playthrough."""

    def __init__(self, message: str = "Access denied for this playthrough"):
        super().__init__(message=message, status_code=403)


class ScenarioNotPublishedError(BaseAppException):
    """Raised when a playthrough is attempted on a non-published scenario."""

    def __init__(self, message: str = "Scenario is not published"):
        super().__init__(message=message, status_code=409)


class InvalidSetupValuesError(BaseAppException):
    """Raised when setup_values fail validation against setup_schema."""

    def __init__(self, message: str = "Invalid setup values"):
        super().__init__(message=message, status_code=422)


class InvalidShareTokenError(BaseAppException):
    """Raised when a share token is missing, unknown, or the wrong mode."""

    def __init__(self, message: str = "Invalid or expired share token"):
        super().__init__(message=message, status_code=404)


class ShareNotFoundError(BaseAppException):
    """Raised when a share_id doesn't exist for the given playthrough."""

    def __init__(self, message: str = "Share link not found"):
        super().__init__(message=message, status_code=404)


class SoloScenarioJoinError(BaseAppException):
    """Raised when joining a scenario that only supports solo play."""

    def __init__(self, message: str = "This scenario does not support multiplayer"):
        super().__init__(message=message, status_code=409)


class PlaythroughNotJoinableError(BaseAppException):
    """Raised when attempting to join a non-active playthrough."""

    def __init__(self, message: str = "This playthrough can no longer be joined"):
        super().__init__(message=message, status_code=409)


class InvalidSchemaInitialError(BaseAppException):
    """Raised when a state_schema or entity attribute `initial` does not fit
    its own field definition, so a playthrough cannot start from it."""

    def __init__(self, field_path: str, reason: str):
        self.field_path = field_path
        self.reason = reason
        super().__init__(
            message=f"Invalid initial value for '{field_path}': {reason}",
            status_code=422,
        )


class InvalidStateOverrideError(BaseAppException):
    """Raised when a playtest's preset state value is unknown or does not fit
    its field, or is sent outside a playtest."""

    def __init__(self, key: str, reason: str):
        super().__init__(message=f"Cannot preset '{key}': {reason}", status_code=422)


class StrategyFactionRequiredError(BaseAppException):
    """Raised when a strategy playthrough names no playable faction."""

    def __init__(
        self, message: str = "Choose a playable faction to start this campaign"
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_code="strategy_faction_invalid",
        )


class StrategyRulerInvalidError(BaseAppException):
    """Raised when the chosen faction's leader cannot rule a campaign."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=422,
            error_code="strategy_ruler_invalid",
        )
