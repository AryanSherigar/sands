"""GET /health. Always unauthenticated."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.models.health import HEALTH_STATUS_OK
from app.services.health_service import HealthService, get_health_service

router = APIRouter()

HTTP_STATUS_OK = 200
HTTP_STATUS_SERVICE_UNAVAILABLE = 503


@router.get("/health")
async def health_check(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> JSONResponse:
    health = await service.check_health()
    is_healthy = health.status == HEALTH_STATUS_OK
    status_code = HTTP_STATUS_OK if is_healthy else HTTP_STATUS_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=health.model_dump())
