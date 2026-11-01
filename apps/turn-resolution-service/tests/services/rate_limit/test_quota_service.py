"""Integration tests for TRS quotas, including exemption by Firebase UID."""

import uuid

import pytest
from app.config import settings
from app.db.models.user import User
from app.exceptions.rate_limit_exceptions import (
    CODE_FEATURE_UNAVAILABLE,
    CODE_QUOTA_EXCEEDED,
    RateLimitExceededError,
)
from app.services.rate_limit.exemption_service import ExemptionService
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService, user_quota_key
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

DAY = 86400


@pytest.fixture
def quota_service(rate_limit_enabled, test_engine) -> QuotaService:
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession)
    return QuotaService(rate_limit_enabled, ExemptionService(factory))


async def test_per_user_quota_exceeded(quota_service, monkeypatch) -> None:
    monkeypatch.setattr(settings, "quota_turn_per_user", 1)
    user_id = uuid.uuid4()
    await quota_service.reserve(QuotaFeature.TURN, user_id)

    with pytest.raises(RateLimitExceededError) as caught:
        await quota_service.reserve(QuotaFeature.TURN, user_id)

    assert caught.value.code == CODE_QUOTA_EXCEEDED
    assert caught.value.scope == "turn"


async def test_exempt_uid_bypasses_user_quota_not_global(
    quota_service, test_engine, monkeypatch
) -> None:
    user_id, firebase_uid = uuid.uuid4(), f"admin-{uuid.uuid4()}"
    async with AsyncSession(test_engine) as session:
        session.add(
            User(user_id=user_id, display_name="Admin", auth_provider_id=firebase_uid)
        )
        await session.commit()
    monkeypatch.setattr(settings, "rate_limit_exempt_firebase_uids", firebase_uid)
    monkeypatch.setattr(settings, "quota_assistant_per_user", 1)
    monkeypatch.setattr(settings, "quota_assistant_global", 2)

    try:
        await quota_service.reserve(QuotaFeature.ASSISTANT, user_id)
        await quota_service.reserve(QuotaFeature.ASSISTANT, user_id)
        with pytest.raises(RateLimitExceededError) as caught:
            await quota_service.reserve(QuotaFeature.ASSISTANT, user_id)
    finally:
        async with AsyncSession(test_engine) as session:
            await session.delete(await session.get(User, user_id))
            await session.commit()

    assert caught.value.code == CODE_FEATURE_UNAVAILABLE


async def test_reserved_refunds_when_ai_call_fails(quota_service) -> None:
    user_id = uuid.uuid4()

    with pytest.raises(RuntimeError):
        async with quota_service.reserved(QuotaFeature.SPEECH_TO_TEXT, user_id):
            raise RuntimeError("speech-to-text down")

    count = await quota_service.store.current_count(
        user_quota_key("speech_to_text", user_id), DAY
    )
    assert count == 0
