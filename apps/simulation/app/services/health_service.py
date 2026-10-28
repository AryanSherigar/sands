"""Health check orchestration: database reachability."""

from typing import Annotated

import psycopg
import structlog
from fastapi import Depends
from psycopg import AsyncConnection

from app.db.pool import get_connection
from app.models.health import HEALTH_STATUS_ERROR, HEALTH_STATUS_OK, HealthResponse
from app.repositories import health_repo

logger = structlog.get_logger()

EVENT_DATABASE_UNREACHABLE = "health_check_database_unreachable"


class HealthService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def check_health(self) -> HealthResponse:
        is_database_reachable = await self._safe_check_database()
        status = HEALTH_STATUS_OK if is_database_reachable else HEALTH_STATUS_ERROR
        return HealthResponse(status=status, database=is_database_reachable)

    async def _safe_check_database(self) -> bool:
        try:
            return await health_repo.is_database_reachable(self._connection)
        except psycopg.Error:
            logger.error(EVENT_DATABASE_UNREACHABLE)
            return False


def get_health_service(
    connection: Annotated[AsyncConnection, Depends(get_connection)],
) -> HealthService:
    return HealthService(connection)
