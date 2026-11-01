"""A truncated player action leaves a durable server-source alpha event."""

import uuid

import pytest
from app.config import settings
from app.db.models.alpha_event import AlphaEvent
from app.db.models.user import User
from app.models.turn import InputTruncation
from app.services.input_limit_event_recorder import InputLimitEventRecorder
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

CONSENT = "alpha-1"
TRUNCATION = InputTruncation(original_length=3000, max_length=2000)


@pytest.fixture
def session_factory(test_engine):
    return async_sessionmaker(bind=test_engine, class_=AsyncSession)


@pytest.fixture
def alpha_mode_on(monkeypatch):
    monkeypatch.setattr(settings, "is_alpha_mode", True)
    monkeypatch.setattr(settings, "alpha_scenario_id", uuid.uuid4())
    monkeypatch.setattr(settings, "alpha_consent_version", CONSENT)


async def _store_user(session_factory, consent: str | None) -> uuid.UUID:
    user_id = uuid.uuid4()
    async with session_factory() as session:
        session.add(
            User(
                user_id=user_id,
                display_name="Tester",
                auth_provider_id=f"uid-{user_id}",
                alpha_consent_version=consent,
            )
        )
        await session.commit()
    return user_id


async def _delete_user(session_factory, user_id: uuid.UUID) -> None:
    async with session_factory() as session:
        await session.delete(await session.get(User, user_id))
        await session.commit()


async def _events_of(session_factory, user_id: uuid.UUID) -> list[AlphaEvent]:
    async with session_factory() as session:
        result = await session.execute(
            select(AlphaEvent).where(AlphaEvent.user_id == user_id)
        )
        return list(result.scalars().all())


async def _record(session_factory, consent: str | None) -> list[AlphaEvent]:
    user_id = await _store_user(session_factory, consent)
    try:
        await InputLimitEventRecorder(session_factory).record_truncated(
            user_id, TRUNCATION
        )
        return await _events_of(session_factory, user_id)
    finally:
        await _delete_user(session_factory, user_id)


async def test_alpha_truncation_writes_a_server_event(
    session_factory, alpha_mode_on
) -> None:
    (event,) = await _record(session_factory, CONSENT)

    assert (event.name, event.source) == ("input_truncated", "server")
    assert event.props == {"original_length": 3000, "max_length": 2000}


async def test_user_without_current_consent_records_nothing(
    session_factory, alpha_mode_on
) -> None:
    assert await _record(session_factory, "alpha-0") == []


async def test_nothing_is_recorded_outside_alpha_mode(session_factory) -> None:
    assert await _record(session_factory, CONSENT) == []


async def test_a_failing_write_never_raises(alpha_mode_on) -> None:
    def broken_factory():
        raise OperationalError("insert", {}, Exception("db down"))

    await InputLimitEventRecorder(broken_factory).record_truncated(
        uuid.uuid4(), TRUNCATION
    )
