"""Scenario music domain exception classes."""

from app.exceptions.base import BaseAppException


class MusicValidationError(BaseAppException):
    """Raised when an uploaded track fails validation."""

    def __init__(self, message: str = "Invalid music track"):
        super().__init__(message=message, status_code=400)
