"""State-schema field-rule exception classes (`hidden`, `initial_random`)."""

from app.exceptions.base import BaseAppException


class SchemaFieldValidationError(BaseAppException):
    """Raised when a state_schema field's `hidden` or `initial_random` setting is
    malformed or contradicts the rest of the schema."""

    def __init__(self, message: str = "Invalid state schema field"):
        super().__init__(message=message, status_code=422)
