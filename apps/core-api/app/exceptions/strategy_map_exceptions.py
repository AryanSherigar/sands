"""Strategy map domain exception classes."""

from app.exceptions.base import BaseAppException


class StrategyMapModeError(BaseAppException):
    """Raised when a strategy map operation targets a non-strategy scenario."""

    def __init__(
        self, message: str = "Region maps are only available for strategy scenarios"
    ):
        super().__init__(message=message, status_code=422)


class StrategyMapInvalidError(BaseAppException):
    """Raised when a traced map fails structural validation."""

    def __init__(self, message: str = "Invalid map"):
        super().__init__(message=message, status_code=422)


class StrategyMapNotFoundError(BaseAppException):
    """Raised when a strategy scenario has no saved map yet."""

    def __init__(self, message: str = "This scenario has no map yet"):
        super().__init__(message=message, status_code=404)
