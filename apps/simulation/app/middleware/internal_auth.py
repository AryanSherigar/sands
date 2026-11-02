"""Service-to-service authentication for internal routes (Core API, TRS)."""

import hmac
from typing import Annotated

from app.config import get_settings
from app.exceptions.auth_exceptions import (
    InternalEndpointDisabledError,
    InvalidInternalTokenError,
)
from fastapi import Header

HEADER_INTERNAL_SERVICE_TOKEN = "X-Internal-Service-Token"


def require_internal_service_token(
    presented: Annotated[str, Header(alias=HEADER_INTERNAL_SERVICE_TOKEN)] = "",
) -> None:
    """Fail closed: an unset token disables the endpoint rather than opening it."""
    expected = get_settings().internal_service_token
    if not expected:
        raise InternalEndpointDisabledError()
    if not hmac.compare_digest(presented.encode(), expected.encode()):
        raise InvalidInternalTokenError()


verify_internal_token = require_internal_service_token
