"""Per-route request body size cap, used as a FastAPI dependency."""

from collections.abc import Awaitable, Callable

from app.exceptions.request_exceptions import PayloadTooLargeError
from fastapi import Request

HEADER_CONTENT_LENGTH = "content-length"


def _declared_length(request: Request) -> int | None:
    declared = request.headers.get(HEADER_CONTENT_LENGTH)
    if declared is None or not declared.isdigit():
        return None
    return int(declared)


def limit_body_size(max_bytes: int) -> Callable[[Request], Awaitable[None]]:
    async def enforce_body_limit(request: Request) -> None:
        declared = _declared_length(request)
        if declared is not None and declared > max_bytes:
            raise PayloadTooLargeError(max_bytes)
        if len(await request.body()) > max_bytes:
            raise PayloadTooLargeError(max_bytes)

    return enforce_body_limit
