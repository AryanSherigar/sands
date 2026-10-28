"""Rule check domain exception classes."""

from app.exceptions.base import BaseAppException


class RuleCheckModeError(BaseAppException):
    """Raised when a rule check operation targets a non-master-mode scenario."""

    def __init__(
        self, message: str = "Rule checks are only available for master-mode scenarios"
    ):
        super().__init__(message=message, status_code=422)


class RuleCheckNotFoundError(BaseAppException):
    """Raised when a rule check is missing or belongs to another scenario."""

    def __init__(self, message: str = "Rule check not found"):
        super().__init__(message=message, status_code=404)


class RuleCheckValidationError(BaseAppException):
    """Raised when a rule check's results, paths or trigger do not fit the
    scenario's state_schema."""

    def __init__(self, message: str = "Invalid rule check configuration"):
        super().__init__(message=message, status_code=422)
