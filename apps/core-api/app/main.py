"""Core API FastAPI Application Entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import close_db_connection
from app.logging_config import configure_logging
from app.middleware.error_handler import setup_error_handlers
from app.middleware.request_context import request_context_middleware

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
    title="Core API",
    description="Core API service for sands platform",
    version="0.1.0",
    lifespan=lifespan,
    **docs_urls(settings.environment),
)

app.middleware("http")(request_context_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After", "RateLimit", "RateLimit-Policy"],
)

setup_error_handlers(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
