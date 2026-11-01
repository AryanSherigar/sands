"""Integration tests for the concurrent SSE stream cap."""

import asyncio

import pytest
from app.config import settings
from app.exceptions.rate_limit_exceptions import RateLimitExceededError
from app.services.rate_limit.store import PostgresRateLimitStore
from app.services.rate_limit.stream_lease_service import StreamLeaseService
from sqlalchemy.exc import OperationalError
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

SUBJECT = "stream:user:test"


async def _events():
    yield ServerSentEvent(event="narration", data="hi")


async def _build() -> EventSourceResponse:
    return EventSourceResponse(_events())


async def _drain(response: EventSourceResponse) -> None:
    async for _ in response.body_iterator:
        pass


async def test_cap_rejects_extra_streams(rate_limit_enabled, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_concurrent_streams_per_user", 2)
    leases = StreamLeaseService(rate_limit_enabled)
    await leases.guard(SUBJECT, _build)
    await leases.guard(SUBJECT, _build)

    with pytest.raises(RateLimitExceededError) as caught:
        await leases.guard(SUBJECT, _build)

    assert caught.value.scope == "concurrent_streams"


async def test_finished_stream_frees_its_slot(rate_limit_enabled, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_concurrent_streams_per_user", 1)
    leases = StreamLeaseService(rate_limit_enabled)

    await _drain(await leases.guard(SUBJECT, _build))

    await leases.guard(SUBJECT, _build)


async def test_failed_build_releases_lease(rate_limit_enabled, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_concurrent_streams_per_user", 1)
    leases = StreamLeaseService(rate_limit_enabled)

    async def _failing_build() -> EventSourceResponse:
        raise RuntimeError("quota exceeded before streaming")

    with pytest.raises(RuntimeError):
        await leases.guard(SUBJECT, _failing_build)

    await leases.guard(SUBJECT, _build)


async def test_concurrent_acquires_respect_cap(
    rate_limit_enabled: PostgresRateLimitStore, monkeypatch
) -> None:
    results = await asyncio.gather(
        *(rate_limit_enabled.acquire_lease("stream:race", 3, 60) for _ in range(10))
    )

    assert sum(lease_id is not None for lease_id in results) == 3


async def test_store_failure_fails_open(rate_limit_enabled, monkeypatch) -> None:
    async def _broken_acquire(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("db down"))

    monkeypatch.setattr(rate_limit_enabled, "acquire_lease", _broken_acquire)
    leases = StreamLeaseService(rate_limit_enabled)

    await _drain(await leases.guard(SUBJECT, _build))
