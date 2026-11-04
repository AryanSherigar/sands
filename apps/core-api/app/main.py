"""Core API FastAPI Application Entrypoint."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.db.connection import close_db_connection
from app.integrations.memory_client import close_memory_client
from app.integrations.simulation_client import close_simulation_client
from app.integrations.storage_client import close_storage_client
from app.logging_config import configure_logging
from app.middleware.error_handler import setup_error_handlers
from app.middleware.internal_proxy import internal_proxy_middleware
from app.middleware.rate_limit import rate_limit_middleware
from app.middleware.request_context import request_context_middleware
from app.routers import (
    auth,
    conditions,
    creator_stats,
    end_conditions,
    entities,
    facts,
    internal_playthroughs,
    invariants,
    logs,
    maps,
    minigames,
    music_defaults,
    playthroughs,
    rule_checks,
    scenario_access,
    scenario_entity_types,
    scenario_music,
    scenario_tools,
    scenarios,
    share,
    sheet_rules,
    strategy_checks,
    strategy_maps,
    strategy_ruler,
    studio_avatar_router,
    uploads,
    users,
)
from app.services.rate_limit.cleanup_service import run_cleanup_forever
from app.services.rate_limit.store import get_rate_limit_store
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

configure_logging(settings.log_level, settings.log_format)


def _start_rate_limit_cleanup() -> asyncio.Task[None] | None:
    if not settings.is_rate_limit_enabled:
        return None
    return asyncio.create_task(run_cleanup_forever(get_rate_limit_store()))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager handling startup and shutdown events."""
    cleanup_task = _start_rate_limit_cleanup()
    yield
    if cleanup_task is not None:
        cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cleanup_task
    await close_db_connection()
    await close_memory_client()
    await close_simulation_client()
    await close_storage_client()


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
app.include_router(auth.router)
app.include_router(scenarios.router)
app.include_router(scenario_access.router)
app.include_router(scenario_music.router)
app.include_router(music_defaults.router)
app.include_router(entities.router)
app.include_router(scenario_entity_types.router)
app.include_router(facts.router)
app.include_router(conditions.router)
app.include_router(end_conditions.router)
app.include_router(invariants.router)
app.include_router(maps.router)
app.include_router(strategy_maps.router)
app.include_router(strategy_checks.router)
app.include_router(strategy_ruler.router)
app.include_router(minigames.router)
app.include_router(rule_checks.router)
app.include_router(sheet_rules.router)
app.include_router(scenario_tools.router)
app.include_router(playthroughs.router)
app.include_router(internal_playthroughs.router)
app.include_router(share.router)
app.include_router(logs.router)
app.include_router(uploads.router)
app.include_router(users.router)
app.include_router(creator_stats.router)
app.include_router(studio_avatar_router.router)

upload_dir = Path(settings.local_upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
