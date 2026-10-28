import asyncio
from uuid import UUID, uuid4

import httpx
import structlog
from app.config import Settings
from app.db.pool import get_pool
from app.models.battle_intelligence import BattleIntent
from app.models.battle_progress import IntentRequest
from app.repositories import intent_request_repo
from app.services.intent_candidate_service import create_candidate
from psycopg import Error as PostgresError

WORKER_CONCURRENCY = 2
logger = structlog.get_logger(__name__)


class IntentWorker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def run(self) -> None:
        while True:
            try:
                requests = await self._claim_batch()
            except (OSError, TimeoutError, httpx.HTTPError, PostgresError):
                await asyncio.sleep(self._settings.intent_worker_poll_seconds)
                continue
            if not requests:
                await asyncio.sleep(self._settings.intent_worker_poll_seconds)
                continue
            try:
                await asyncio.gather(*(self._process(request) for request in requests))
            except (OSError, PostgresError):
                await asyncio.sleep(self._settings.intent_worker_poll_seconds)

    async def _claim_batch(self) -> list[IntentRequest]:
        async with get_pool().connection() as connection, connection.transaction():
            return await intent_request_repo.claim_requests(
                connection, uuid4(), WORKER_CONCURRENCY
            )

    async def _process(self, request: IntentRequest) -> None:
        lease_token = request.lease_token
        if lease_token is None:
            logger.error("claimed strategy intent is missing its lease")
            return
        try:
            candidate = await create_candidate(request, self._settings)
            await self._record_candidate(request, lease_token, candidate)
        except (httpx.HTTPError, TimeoutError, ValueError) as error:
            logger.warning(
                "strategy intent provider failed",
                request_id=request.request_id,
                error_type=type(error).__name__,
            )
            await self._record_fallback(request, lease_token)

    async def _record_candidate(
        self, request: IntentRequest, lease_token: UUID, candidate: BattleIntent
    ) -> None:
        async with get_pool().connection() as connection, connection.transaction():
            was_recorded = await intent_request_repo.complete_request(
                connection,
                request.playthrough_id,
                request.request_id,
                lease_token,
                candidate,
            )
        if not was_recorded:
            logger.info(
                "strategy intent answer arrived after freeze",
                request_id=request.request_id,
            )

    async def _record_fallback(self, request: IntentRequest, lease_token: UUID) -> None:
        async with get_pool().connection() as connection, connection.transaction():
            await intent_request_repo.fail_request(
                connection,
                request.playthrough_id,
                request.request_id,
                lease_token,
            )
