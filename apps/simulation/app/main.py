"""Simulation service FastAPI application entrypoint."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from app.config import Settings, get_settings
from app.db.pool import close_pool, open_pool
from app.integrations.core_api_client import close_core_api_client
from app.logging import configure_logging
from app.middleware.error_handler import setup_error_handlers
from app.routers import (
    battles,
    campaign,
    commands,
    dispatches,
    epilogue,
    events_narrative,
    health,
    internal_art,
    internal_dispatches,
    internal_epilogue,
    internal_playthroughs,
    internal_scenes,
    internal_summaries,
    proclamation_scene,
    replay,
    scenes,
    summaries,
    turn_reports,
)
from app.services.intent_worker import IntentWorker
from app.services.stance_service import is_stance_provider_ready
from app.services.stance_worker import StanceWorker
from fastapi import FastAPI

SERVICE_TITLE = "Simulation Service"
SERVICE_DESCRIPTION = "Deterministic strategy-mode simulation for the sands platform"
SERVICE_VERSION = "0.1.0"


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    await open_pool()
    worker_tasks = _start_workers(settings)
    try:
        yield
    finally:
        for worker_task in worker_tasks:
            worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await worker_task
        await close_core_api_client()
        await close_pool()


def _start_workers(settings: Settings) -> list[asyncio.Task[None]]:
    tasks: list[asyncio.Task[None]] = []
    if _intent_worker_enabled(settings):
        tasks.append(asyncio.create_task(IntentWorker(settings).run()))
    if _stance_worker_enabled(settings):
        tasks.append(asyncio.create_task(StanceWorker(settings).run()))
    return tasks


def _stance_worker_enabled(settings: Settings) -> bool:
    return is_stance_provider_ready(settings)


def _intent_worker_enabled(settings: Settings) -> bool:
    return bool(
        settings.intent_provider_enabled
        and settings.intent_provider_url
        and settings.intent_provider_api_key
        and settings.intent_provider_model
    )


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
    for route in (
        health,
        internal_playthroughs,
        internal_scenes,
        internal_art,
        internal_dispatches,
        internal_summaries,
        internal_epilogue,
        summaries,
        epilogue,
        dispatches,
        campaign,
        battles,
        commands,
        events_narrative,
        replay,
        turn_reports,
        scenes,
        proclamation_scene,
    ):
        application.include_router(route.router)
    return application


app = create_app()
