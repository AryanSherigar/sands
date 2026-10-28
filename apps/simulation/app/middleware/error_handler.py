"""Maps domain exceptions to HTTP responses. The only file that does this translation."""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions.base import SimulationServiceError

logger = structlog.get_logger()

EVENT_DOMAIN_EXCEPTION = "domain_exception"
EVENT_UNHANDLED_EXCEPTION = "unhandled_exception"
HTTP_STATUS_INTERNAL_SERVER_ERROR = 500
MESSAGE_INTERNAL_SERVER_ERROR = "Internal server error"


def setup_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SimulationServiceError)
    async def simulation_service_exception_handler(
        request: Request, exc: SimulationServiceError
    ) -> JSONResponse:
        logger.warning(EVENT_DOMAIN_EXCEPTION, path=request.url.path, exc_info=exc)
        content: dict[str, object] = {"detail": exc.message}
        if exc.code is not None:
            content["code"] = exc.code
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(EVENT_UNHANDLED_EXCEPTION, path=request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=HTTP_STATUS_INTERNAL_SERVER_ERROR,
            content={"detail": MESSAGE_INTERNAL_SERVER_ERROR},
        )
