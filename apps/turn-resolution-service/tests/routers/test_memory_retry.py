"""POST /v1/playthroughs/{id}/memory/retry against a real test Postgres."""

import uuid

import pytest
from app.config import settings
from app.db.models.memory_outbox import MemoryOutbox
from app.exceptions.memory_exceptions import MemoryRetryError
from app.integrations import memory_client
from app.models.memory_retry import MemoryRetryResult
from app.services import memory_relay_service
from app.services.rate_limit.policies import match_burst_policy
from httpx import AsyncClient
from memory_outbox_factories import SeededPlaythrough, seed_playthrough
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _Spy:
    def __init__(self, reasons: list[str] | None = None) -> None:
        self.retry_calls: list[uuid.UUID] = []
        self.relay_calls: list[uuid.UUID] = []
        self._reasons = reasons or []

    async def retry_memory(self, playthrough_id: uuid.UUID) -> MemoryRetryResult:
        self.retry_calls.append(playthrough_id)
        return MemoryRetryResult(batches_reset=1, degraded_reasons=self._reasons)

    async def deliver_best_effort(self, playthrough_id: uuid.UUID) -> None:
        self.relay_calls.append(playthrough_id)


@pytest.fixture
def spy(monkeypatch) -> _Spy:
    instance = _Spy(["extraction_failed"])
    monkeypatch.setattr(memory_client, "retry_memory", instance.retry_memory)
    monkeypatch.setattr(
        memory_relay_service, "deliver_best_effort", instance.deliver_best_effort
    )
    return instance


def _url(seeded: SeededPlaythrough) -> str:
    return f"/v1/playthroughs/{seeded.playthrough_id}/memory/retry"


async def test_participant_retry_relays_then_returns_the_remaining_reasons(
    async_client: AsyncClient, db_session: AsyncSession, spy: _Spy
) -> None:
    seeded = await seed_playthrough(db_session)

    response = await async_client.post(
        _url(seeded), headers={"x-dev-user-id": str(seeded.user_id)}
    )

    assert response.status_code == 200
    assert response.json() == {"degraded_reasons": ["extraction_failed"]}
    assert spy.relay_calls == [seeded.playthrough_id]
    assert spy.retry_calls == [seeded.playthrough_id]


async def test_non_member_gets_403_and_nothing_is_called(
    async_client: AsyncClient, db_session: AsyncSession, spy: _Spy
) -> None:
    seeded = await seed_playthrough(db_session)

    response = await async_client.post(
        _url(seeded), headers={"x-dev-user-id": str(uuid.uuid4())}
    )

    assert response.status_code == 403
    assert spy.retry_calls == [] and spy.relay_calls == []


async def test_unauthenticated_request_is_401(
    async_client: AsyncClient, db_session: AsyncSession, spy: _Spy
) -> None:
    seeded = await seed_playthrough(db_session)

    response = await async_client.post(_url(seeded))

    assert response.status_code == 401


async def test_unregistered_legacy_playthrough_has_nothing_to_retry(
    async_client: AsyncClient, db_session: AsyncSession, spy: _Spy
) -> None:
    seeded = await seed_playthrough(db_session)
    from app.db.models.playthrough import Playthrough

    playthrough = await db_session.get(Playthrough, seeded.playthrough_id)
    playthrough.memory_publish_revision = None
    await db_session.commit()

    response = await async_client.post(
        _url(seeded), headers={"x-dev-user-id": str(seeded.user_id)}
    )

    assert response.json() == {"degraded_reasons": []}
    assert spy.retry_calls == []


async def test_memory_failure_surfaces_as_502(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    async def _fail(playthrough_id):
        raise MemoryRetryError("unavailable")

    async def _noop(playthrough_id):
        return None

    monkeypatch.setattr(memory_client, "retry_memory", _fail)
    monkeypatch.setattr(memory_relay_service, "deliver_best_effort", _noop)
    seeded = await seed_playthrough(db_session)

    response = await async_client.post(
        _url(seeded), headers={"x-dev-user-id": str(seeded.user_id)}
    )

    assert response.status_code == 502


async def test_lagging_outbox_rows_add_delivery_lag(
    async_client: AsyncClient, db_session: AsyncSession, spy: _Spy, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "recent_window_turns", 2)
    seeded = await seed_playthrough(db_session)
    from app.db.models.playthrough import Playthrough

    playthrough = await db_session.get(Playthrough, seeded.playthrough_id)
    playthrough.turn_count = 5
    db_session.add(
        MemoryOutbox(
            playthrough_id=seeded.playthrough_id,
            item_kind="turn",
            sequence=1,
            turn_id=uuid.uuid4(),
            payload={},
        )
    )
    await db_session.commit()

    response = await async_client.post(
        _url(seeded), headers={"x-dev-user-id": str(seeded.user_id)}
    )

    assert response.json() == {
        "degraded_reasons": ["extraction_failed", "delivery_lag"]
    }


async def test_retry_path_has_its_own_burst_policy() -> None:
    policy = match_burst_policy(
        "POST", f"/v1/playthroughs/{uuid.uuid4()}/memory/retry", True
    )

    assert policy.group == "memory_retry"
    assert policy.limit == settings.rate_limit_memory_retry_per_window
