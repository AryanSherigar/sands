"""Map generation domain exception classes."""

from app.exceptions.base import BaseAppException


class InvalidRegionImageError(BaseAppException):
    """Raised when a region image is not a usable PNG within the size limit."""

    def __init__(self, message: str = "The region image is not a valid PNG"):
        super().__init__(message=message, status_code=400)


class MapJobNotFoundError(BaseAppException):
    """Raised when a map generation job does not exist or is not the caller's."""

    def __init__(self, message: str = "Map generation job not found"):
        super().__init__(message=message, status_code=404)
