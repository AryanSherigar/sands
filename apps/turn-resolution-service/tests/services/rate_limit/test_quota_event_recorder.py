"""A tripped quota leaves a durable server-source alpha event."""

import uuid

import pytest
from app.config import settings
from app.db.models.alpha_event import AlphaEvent
from app.db.models.user import User
from app.exceptions.rate_limit_exceptions import RateLimitExceededError
from app.services.rate_limit.exemption_service import ExemptionService
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_event_recorder import QuotaEventRecorder
from app.services.rate_limit.quota_service import QuotaService
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

CONSENT = "alpha-1"


@pytest.fixture
def session_factory(test_engine):
    return async_sessionmaker(bind=test_engine, class_=AsyncSession)


@pytest.fixture
def quota_service(rate_limit_enabled, session_factory) -> QuotaService:
    return QuotaService(
        rate_limit_enabled,
        ExemptionService(session_factory),
        QuotaEventRecorder(session_factory),
    )


@pytest.fixture
def alpha_mode_on(monkeypatch):
    monkeypatch.setattr(settings, "is_alpha_mode", True)
    monkeypatch.setattr(settings, "alpha_scenario_id", uuid.uuid4())
    monkeypatch.setattr(settings, "alpha_consent_version", CONSENT)
    monkeypatch.setattr(settings, "quota_turn_per_user", 1)


@pytest.fixture
async def tester(session_factory):
    user_id = uuid.uuid4()
    await _store_user(session_factory, user_id, CONSENT)
    yield user_id
    await _delete_user(session_factory, user_id)


async def _store_user(session_factory, user_id: uuid.UUID, consent: str | None) -> None:
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


async def _delete_user(session_factory, user_id: uuid.UUID) -> None:
    async with session_factory() as session:
        await session.delete(await session.get(User, user_id))
        await session.commit()


async def _trip_turn_quota(quota_service: QuotaService, user_id: uuid.UUID) -> None:
    await quota_service.reserve(QuotaFeature.TURN, user_id)
    with pytest.raises(RateLimitExceededError):
        await quota_service.reserve(QuotaFeature.TURN, user_id)


async def _events_of(session_factory, user_id: uuid.UUID) -> list[AlphaEvent]:
    async with session_factory() as session:
        result = await session.execute(
            select(AlphaEvent).where(AlphaEvent.user_id == user_id)
        )
        return list(result.scalars().all())


async def test_a_tripped_user_quota_writes_a_server_event(
    quota_service, session_factory, tester, alpha_mode_on
) -> None:
    await _trip_turn_quota(quota_service, tester)

    (event,) = await _events_of(session_factory, tester)
    assert (event.name, event.source, event.session_id) == (
        "quota_exceeded",
        "server",
        "server",
    )
    assert event.props == {"feature": "turn", "scope": "user"}
    assert event.playthrough_id is None


async def test_a_tripped_global_cap_is_recorded_with_global_scope(
    quota_service, session_factory, tester, alpha_mode_on, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "quota_turn_per_user", 100)
    monkeypatch.setattr(settings, "quota_turn_global", 1)

    await _trip_turn_quota(quota_service, tester)

    (event,) = await _events_of(session_factory, tester)
    assert event.props["scope"] == "global"


async def test_a_user_without_current_consent_records_nothing(
    quota_service, session_factory, alpha_mode_on
) -> None:
    user_id = uuid.uuid4()
    await _store_user(session_factory, user_id, "alpha-0")
    try:
        await _trip_turn_quota(quota_service, user_id)
        events = await _events_of(session_factory, user_id)
    finally:
        await _delete_user(session_factory, user_id)

    assert events == []


async def test_nothing_is_recorded_outside_alpha_mode(
    quota_service, session_factory, tester, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "quota_turn_per_user", 1)

    await _trip_turn_quota(quota_service, tester)

    assert await _events_of(session_factory, tester) == []


async def test_a_failing_event_write_never_changes_the_quota_error(
    rate_limit_enabled, session_factory, tester, alpha_mode_on
) -> None:
    def broken_factory():
        raise OperationalError("insert", {}, Exception("db down"))

    service = QuotaService(
        rate_limit_enabled,
        ExemptionService(session_factory),
        QuotaEventRecorder(broken_factory),
    )

    await _trip_turn_quota(service, tester)
