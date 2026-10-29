"""Memory service FastAPI application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.config import get_settings
from app.db.pool import close_pool, open_pool
from app.logging import configure_logging
from app.middleware.error_handler import setup_error_handlers
from app.routers import (
    health,
    ingest,
    jobs,
    playthroughs,
    purge,
    retrieve,
    templates,
)
from app.services.extraction_service import get_extraction_queue
from fastapi import FastAPI

SERVICE_TITLE = "Memory Service"
SERVICE_DESCRIPTION = "Greenfield memory service for the sands platform"
SERVICE_VERSION = "0.1.0"


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    pool = await open_pool()
    queue = get_extraction_queue()
    await queue.open(pool)
    yield
    await queue.close()
    await close_pool()


def create_app() -> FastAPI:
    """Build the FastAPI app: configure logging, wire the pool lifespan, register routes."""
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=SERVICE_TITLE,
        description=SERVICE_DESCRIPTION,
        version=SERVICE_VERSION,
        lifespan=_lifespan,
    )
    setup_error_handlers(application)
    application.include_router(health.router)
    application.include_router(ingest.router)
    application.include_router(templates.router)
    application.include_router(jobs.router)
    application.include_router(retrieve.router)
    application.include_router(playthroughs.router)
    application.include_router(purge.router)
    return application


app = create_app()
