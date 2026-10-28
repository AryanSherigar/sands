import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from uuid import uuid4

import httpx
import structlog
from app.config import Settings
from app.db.pool import get_pool
from app.integrations.llm_client import StanceProviderClient
from app.models.stance import StanceChoice, StanceRequest, StanceSource
from app.repositories import stance_request_repo
from app.services.stance_service import create_stance_candidate
from psycopg import AsyncConnection
from psycopg import Error as PostgresError

WORKER_CONCURRENCY = 2
logger = structlog.get_logger(__name__)

ConnectionFactory = Callable[[], AbstractAsyncContextManager[AsyncConnection]]


def _pool_connection() -> AbstractAsyncContextManager[AsyncConnection]:
    return get_pool().connection()


class StanceWorker:
    def __init__(
        self,
        settings: Settings,
        client: StanceProviderClient | None = None,
        connection_factory: ConnectionFactory = _pool_connection,
    ) -> None:
        self._settings = settings
        self._client = client
        self._connection_factory = connection_factory

    async def run(self) -> None:
        while True:
            try:
                processed = await self.run_once()
            except (OSError, TimeoutError, httpx.HTTPError, PostgresError):
                processed = 0
            if processed == 0:
                await asyncio.sleep(self._settings.stance_worker_poll_seconds)

    async def run_once(self) -> int:
        requests = await self._claim_batch()
        await asyncio.gather(*(self.process_request(item) for item in requests))
        return len(requests)

    async def process_request(self, request: StanceRequest) -> bool:
        candidate = await create_stance_candidate(request, self._settings, self._client)
        was_recorded = await self._record(request, candidate)
        if not was_recorded:
            logger.info(
                "stance answer arrived after freeze", request_id=request.request_id
            )
        return was_recorded

    async def _claim_batch(self) -> list[StanceRequest]:
        async with self._connection_factory() as connection, connection.transaction():
            return await stance_request_repo.claim_requests(
                connection, uuid4(), WORKER_CONCURRENCY
            )

    async def _record(self, request: StanceRequest, candidate: StanceChoice) -> bool:
        lease_token = request.lease_token
        if lease_token is None:
            logger.error("claimed stance request is missing its lease")
            return False
        async with self._connection_factory() as connection, connection.transaction():
            if candidate.source is StanceSource.FALLBACK:
                return await stance_request_repo.fail_request(
                    connection, request.playthrough_id, request.request_id, lease_token
                )
            return await stance_request_repo.complete_request(
                connection,
                request.playthrough_id,
                request.request_id,
                lease_token,
                candidate,
            )
