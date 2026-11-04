import structlog
from app.exceptions.base import BaseAppException
from app.exceptions.rate_limit_exceptions import (
    QuotaStoreUnavailableError,
    RateLimitExceededError,
)
from app.middleware.rate_limit_headers import (
    build_quota_unavailable_response,
    build_rate_limit_response,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger()

EVENT_UNHANDLED_EXCEPTION = "unhandled_exception"


def setup_error_handlers(app: FastAPI):
    @app.exception_handler(RateLimitExceededError)
    async def rate_limit_exception_handler(
        request: Request, exc: RateLimitExceededError
    ) -> JSONResponse:
        return build_rate_limit_response(exc)

    @app.exception_handler(QuotaStoreUnavailableError)
    async def quota_unavailable_exception_handler(
        request: Request, exc: QuotaStoreUnavailableError
    ) -> JSONResponse:
        return build_quota_unavailable_response(exc)

    @app.exception_handler(BaseAppException)
    async def app_exception_handler(request: Request, exc: BaseAppException):
        logger.warning("domain_exception", path=request.url.path, exc_info=exc)
        content: dict[str, str] = {"detail": exc.message}
        if exc.error_code is not None:
            content["code"] = exc.error_code
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(EVENT_UNHANDLED_EXCEPTION, path=request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
