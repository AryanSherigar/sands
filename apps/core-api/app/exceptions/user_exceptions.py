"""User domain exceptions."""

from app.exceptions.base import BaseAppException


class UserNotFoundError(BaseAppException):
    """Raised when a user is not found by ID."""

    def __init__(self, message: str = "User not found") -> None:
        super().__init__(message, status_code=404)
