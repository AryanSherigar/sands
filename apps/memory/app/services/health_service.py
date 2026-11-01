"""Health check orchestration: combines DB reachability and required extensions."""

from typing import Annotated

import psycopg
import structlog
from app.db.pool import get_connection
from app.models.health import (
    HEALTH_STATUS_ERROR,
    HEALTH_STATUS_OK,
    HealthExtensions,
    HealthResponse,
)
from app.repositories import health_repo
from app.repositories.health_repo import REQUIRED_EXTENSION_NAMES
from fastapi import Depends
from psycopg import AsyncConnection

logger = structlog.get_logger()

EVENT_DATABASE_UNREACHABLE = "health_check_database_unreachable"
EVENT_EXTENSIONS_QUERY_FAILED = "health_check_extensions_query_failed"


class HealthService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def check_health(self) -> HealthResponse:
        is_database_reachable = await self._safe_check_database()
        installed_extensions = await self._safe_get_extensions(is_database_reachable)
        extensions = HealthExtensions(
            vector="vector" in installed_extensions,
            pg_textsearch="pg_textsearch" in installed_extensions,
        )
        is_healthy = is_database_reachable and all(
            name in installed_extensions for name in REQUIRED_EXTENSION_NAMES
        )
        status = HEALTH_STATUS_OK if is_healthy else HEALTH_STATUS_ERROR
        return HealthResponse(
            status=status, database=is_database_reachable, extensions=extensions
        )

    async def _safe_check_database(self) -> bool:
        try:
            return await health_repo.is_database_reachable(self._connection)
        except psycopg.Error:
            logger.error(EVENT_DATABASE_UNREACHABLE)
            return False

    async def _safe_get_extensions(self, is_database_reachable: bool) -> set[str]:
        if not is_database_reachable:
            return set()
        try:
            return await health_repo.get_installed_extensions(self._connection)
        except psycopg.Error:
            logger.error(EVENT_EXTENSIONS_QUERY_FAILED)
            return set()


def get_health_service(
    connection: Annotated[AsyncConnection, Depends(get_connection)],
) -> HealthService:
    return HealthService(connection)
