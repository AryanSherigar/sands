from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from app.models.stance import StanceSource
from app.repositories import stance_request_repo
from app.services.stance_worker import StanceWorker
from psycopg import AsyncConnection
from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import seed_playthrough
from tests.services.stance_fixtures import (
    FakeStanceClient,
    ready_settings,
    stance_request,
)


def _worker(connection: AsyncConnection, client: FakeStanceClient) -> StanceWorker:
    @asynccontextmanager
    async def shared() -> AsyncIterator[AsyncConnection]:
        yield connection

    return StanceWorker(ready_settings(), client=client, connection_factory=shared)


async def test_worker_completes_pending_request(db_connection: AsyncConnection) -> None:
    await seed_playthrough(db_connection)
    await stance_request_repo.insert_request(db_connection, stance_request())
    processed = await _worker(db_connection, FakeStanceClient("expand")).run_once()
    frozen = await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
    assert processed == 1
    assert (frozen["mira"].option_id, frozen["mira"].source) == (
        "expand",
        StanceSource.MODEL,
    )


async def test_worker_records_fallback_on_provider_failure(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    await stance_request_repo.insert_request(db_connection, stance_request())
    client = FakeStanceClient(error=TimeoutError())
    await _worker(db_connection, client).run_once()
    frozen = await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
    cursor = await db_connection.execute("SELECT state FROM stance_requests")
    assert frozen["mira"].source is StanceSource.FALLBACK
    assert await cursor.fetchone() == ("fallback",)


async def test_late_completion_after_activation_is_dropped(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    await stance_request_repo.insert_request(db_connection, stance_request())
    claimed = await stance_request_repo.claim_requests(db_connection, uuid4(), 5)
    await stance_request_repo.activate_stances(db_connection, PLAYTHROUGH_ID, 1)
    worker = _worker(db_connection, FakeStanceClient("expand"))
    with structlog.testing.capture_logs() as logs:
        was_recorded = await worker.process_request(claimed[0])
    frozen = await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
    assert was_recorded is False
    assert frozen["mira"].source is StanceSource.FALLBACK
    assert any(entry["event"] == "stance answer arrived after freeze" for entry in logs)


async def test_run_once_with_nothing_pending_returns_zero(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    assert await _worker(db_connection, FakeStanceClient("expand")).run_once() == 0
