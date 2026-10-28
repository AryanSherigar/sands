"""Simulation service FastAPI application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db.pool import close_pool, open_pool
from app.logging import configure_logging
from app.middleware.error_handler import setup_error_handlers
from app.routers import health

SERVICE_TITLE = "Simulation Service"
SERVICE_DESCRIPTION = "Deterministic strategy-mode simulation for the sands platform"
SERVICE_VERSION = "0.1.0"


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await open_pool()
    yield
    await close_pool()


def create_app() -> FastAPI:
    """Build the FastAPI app: configure logging, wire the pool lifespan, register routes."""
    configure_logging(get_settings().log_level)
    application = FastAPI(
        title=SERVICE_TITLE,
        description=SERVICE_DESCRIPTION,
        version=SERVICE_VERSION,
        lifespan=_lifespan,
    )
    setup_error_handlers(application)
    application.include_router(health.router)
    return application


app = create_app()
