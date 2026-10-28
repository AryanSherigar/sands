"""Request-shape exceptions not tied to one domain."""

from app.exceptions.base import BaseAppException


class PayloadTooLargeError(BaseAppException):
    def __init__(self, max_bytes: int) -> None:
        super().__init__(
            message=f"Request body exceeds the {max_bytes}-byte limit.",
            status_code=413,
        )
