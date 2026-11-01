import asyncio

from app import main
from app.config import Settings
from fastapi import FastAPI
from pytest import MonkeyPatch

from tests.services.stance_fixtures import ready_settings


async def test_lifespan_leaves_stance_worker_disabled_by_default(
    monkeypatch: MonkeyPatch,
) -> None:
    async def noop() -> None:
        return None

    monkeypatch.setattr(main, "get_settings", Settings)
    monkeypatch.setattr(main, "open_pool", noop)
    monkeypatch.setattr(main, "close_pool", noop)

    async with main._lifespan(FastAPI()):
        assert main._stance_worker_enabled(Settings()) is False


async def test_lifespan_cancels_enabled_stance_worker_before_closing_pool(
    monkeypatch: MonkeyPatch,
) -> None:
    started = asyncio.Event()
    stopped = asyncio.Event()
    pool_closed = asyncio.Event()
    settings = ready_settings()

    class FakeWorker:
        def __init__(self, worker_settings: Settings) -> None:
            assert worker_settings is settings

        async def run(self) -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

    async def open_pool() -> None:
        return None

    async def close_pool() -> None:
        assert stopped.is_set()
        pool_closed.set()

    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "StanceWorker", FakeWorker)
    monkeypatch.setattr(main, "open_pool", open_pool)
    monkeypatch.setattr(main, "close_pool", close_pool)

    async with main._lifespan(FastAPI()):
        await asyncio.wait_for(started.wait(), timeout=0.1)

    assert stopped.is_set()
    assert pool_closed.is_set()
