"""Text generation domain exceptions."""

from app.exceptions.base import BaseAppException


class TextGenerationError(BaseAppException):
    """Raised when AI text generation fails."""

    def __init__(self, message: str = "Text generation is temporarily unavailable"):
        super().__init__(message=message, status_code=502)
