"""Internal endpoint the compose sweep calls to relay pending memory outbox rows."""

import hmac
from typing import Annotated

from app.config import settings
from app.exceptions.memory_exceptions import (
    InternalEndpointDisabledError,
    InvalidInternalTokenError,
)
from app.models.memory_relay import RelaySummary
from app.services.memory_relay_service import MemoryRelayService, get_relay_service
from fastapi import APIRouter, Depends, Header

HEADER_INTERNAL_SERVICE_TOKEN = "X-Internal-Service-Token"

router = APIRouter(prefix="/internal/memory", tags=["Internal"])


def require_internal_service_token(
    presented: Annotated[str, Header(alias=HEADER_INTERNAL_SERVICE_TOKEN)] = "",
) -> None:
    """Fail closed: an unset token disables the endpoint rather than opening it."""
    if not settings.internal_service_token:
        raise InternalEndpointDisabledError()
    is_match = hmac.compare_digest(
        presented.encode(), settings.internal_service_token.encode()
    )
    if not is_match:
        raise InvalidInternalTokenError()


@router.post("/relay", response_model=RelaySummary)
async def relay_pending_memory_rows(
    _: Annotated[None, Depends(require_internal_service_token)],
    relay_service: Annotated[MemoryRelayService, Depends(get_relay_service)],
) -> RelaySummary:
    """Deliver pending outbox rows for every playthrough that has any."""
    return await relay_service.deliver_pending()
