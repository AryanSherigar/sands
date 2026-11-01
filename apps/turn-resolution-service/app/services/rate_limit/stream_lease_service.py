"""Cap on simultaneously open SSE streams per user (or per IP when anonymous).

A lease is taken before the response is built, renewed while the stream is
open, and deleted when it closes. Leases carry an expiry, so a crashed
instance can hold a slot for at most stream_lease_ttl_seconds. Store failures
fail open: a stream is not an AI cost, and quotas guard those separately.
"""

import asyncio
import contextlib
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable

import structlog
from app.config import settings
from app.exceptions.rate_limit_exceptions import (
    CODE_RATE_LIMITED,
    LimitPolicy,
    RateLimitExceededError,
)
from app.services.rate_limit.store import (
    EVENT_RATE_LIMIT_STORE_ERROR,
    STORE_ERRORS,
    RateLimitStore,
    get_rate_limit_store,
)
from fastapi import Depends
from sse_starlette.sse import EventSourceResponse

logger = structlog.get_logger()

STREAM_SCOPE = "concurrent_streams"
STREAM_RETRY_AFTER_SECONDS = 5
TOO_MANY_STREAMS_MESSAGE = (
    "Too many live connections are open. Close another tab and try again."
)


def stream_subject_for_user(user_id: uuid.UUID) -> str:
    return f"stream:user:{user_id}"


def stream_subject_for_ip(ip: str) -> str:
    return f"stream:ip:{ip}"


class StreamLeaseService:
    def __init__(self, store: RateLimitStore) -> None:
        self.store = store

    async def guard(
        self,
        subject_key: str,
        build_response: Callable[[], Awaitable[EventSourceResponse]],
    ) -> EventSourceResponse:
        """Build a stream response that holds a lease for its whole lifetime."""
        lease_id = await self._acquire(subject_key)
        try:
            response = await build_response()
        except BaseException:
            await self._release(lease_id)
            raise
        response.body_iterator = self._hold(lease_id, response.body_iterator)
        return response

    async def _acquire(self, subject_key: str) -> uuid.UUID | None:
        if not settings.is_rate_limit_enabled:
            return None
        try:
            lease_id = await self.store.acquire_lease(
                subject_key,
                settings.max_concurrent_streams_per_user,
                settings.stream_lease_ttl_seconds,
            )
        except STORE_ERRORS as error:
            logger.error(
                EVENT_RATE_LIMIT_STORE_ERROR, scope=STREAM_SCOPE, error=str(error)
            )
            return None
        if lease_id is None:
            raise _too_many_streams_error()
        return lease_id

    async def _hold(
        self, lease_id: uuid.UUID | None, body: AsyncIterator[object]
    ) -> AsyncIterator[object]:
        renewer = asyncio.create_task(self._renew_forever(lease_id))
        try:
            async for item in body:
                yield item
        finally:
            renewer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await renewer
            await self._release(lease_id)

    async def _renew_forever(self, lease_id: uuid.UUID | None) -> None:
        if lease_id is None:
            return
        while True:
            await asyncio.sleep(settings.sse_ping_interval_seconds)
            try:
                await self.store.renew_lease(
                    lease_id, settings.stream_lease_ttl_seconds
                )
            except STORE_ERRORS as error:
                logger.error(
                    EVENT_RATE_LIMIT_STORE_ERROR, scope=STREAM_SCOPE, error=str(error)
                )

    async def _release(self, lease_id: uuid.UUID | None) -> None:
        if lease_id is None:
            return
        try:
            await self.store.release_lease(lease_id)
        except STORE_ERRORS as error:
            logger.error(
                EVENT_RATE_LIMIT_STORE_ERROR, scope=STREAM_SCOPE, error=str(error)
            )


def _too_many_streams_error() -> RateLimitExceededError:
    return RateLimitExceededError(
        TOO_MANY_STREAMS_MESSAGE,
        code=CODE_RATE_LIMITED,
        scope=STREAM_SCOPE,
        reset_at=None,
        retry_after_seconds=STREAM_RETRY_AFTER_SECONDS,
        policy=LimitPolicy(
            limit=settings.max_concurrent_streams_per_user,
            window_seconds=settings.stream_lease_ttl_seconds,
        ),
    )


def get_stream_lease_service(
    store: RateLimitStore = Depends(get_rate_limit_store),
) -> StreamLeaseService:
    return StreamLeaseService(store)
