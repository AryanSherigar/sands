"""Global exception and error response middleware."""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions.base import BaseAppException

logger = structlog.get_logger()

EVENT_UNHANDLED_EXCEPTION = "unhandled_exception"


def setup_error_handlers(app: FastAPI) -> None:
    """Register application-wide exception handlers on the FastAPI application."""

    @app.exception_handler(BaseAppException)
    async def app_exception_handler(
        request: Request, exc: BaseAppException
    ) -> JSONResponse:
        logger.warning("domain_exception", path=request.url.path, exc_info=exc)
        content: dict[str, str] = {"detail": exc.message}
        if exc.error_code is not None:
            content["code"] = exc.error_code
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(EVENT_UNHANDLED_EXCEPTION, path=request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
