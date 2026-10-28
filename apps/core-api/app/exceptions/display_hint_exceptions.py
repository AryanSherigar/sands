"""Display-hint (tool `status_hud`) exception classes."""

from app.exceptions.base import BaseAppException


class DisplayHintValidationError(BaseAppException):
    """Raised when a state_schema field's `display` hint is malformed or
    contradicts the rest of the schema."""

    def __init__(self, message: str = "Invalid display hint"):
        super().__init__(message=message, status_code=422)
