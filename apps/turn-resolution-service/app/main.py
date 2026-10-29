"""Turn Resolution Service FastAPI Application Entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.config import settings
from app.db.connection import close_db_connection
from app.logging_config import configure_logging
from app.middleware.error_handler import setup_error_handlers
from app.middleware.internal_proxy import internal_proxy_middleware
from app.middleware.rate_limit import rate_limit_middleware
from app.middleware.request_context import request_context_middleware
from app.routers import (
    assistant,
    combat,
    internal_memory,
    memory_retry,
    scene,
    session,
    strategy_summaries,
    turn,
    voice,
    welcome,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

configure_logging(settings.log_level, settings.log_format)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager handling startup and shutdown events."""
    yield
    await close_db_connection()


PRODUCTION_ENVIRONMENT = "production"


def docs_urls(environment: str) -> dict[str, str | None]:
    if environment == PRODUCTION_ENVIRONMENT:
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}


app = FastAPI(
    title="Turn Resolution Service",
    description="Turn Resolution Service for sands platform",
    version="0.1.0",
    lifespan=lifespan,
    **docs_urls(settings.environment),
)

# NOTE: Required now that this service has a real HTTP entrypoint the frontend
# calls directly from the browser (POST /v1/turn, session SSE) — previously
# unnecessary since nothing outside tests reached this app over HTTP.
# NOTE: Starlette runs the last-registered middleware first, so the effective
# order is CORS -> internal proxy gate -> request context -> rate limit. CORS
# stays outermost so a 403/429 still carries CORS headers for the dev server.
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(request_context_middleware)
app.middleware("http")(internal_proxy_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After", "RateLimit", "RateLimit-Policy"],
)

setup_error_handlers(app)
app.include_router(turn.router)
app.include_router(combat.router)
app.include_router(strategy_summaries.router)
app.include_router(session.router)
app.include_router(assistant.router)
app.include_router(scene.router)
app.include_router(voice.router)
app.include_router(welcome.router)
app.include_router(internal_memory.router)
app.include_router(memory_retry.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
