"""Integration tests for daily quotas, global caps, refunds and fail-closed."""

import uuid

import pytest
from app.config import settings
from app.db.models.user import User
from app.exceptions.rate_limit_exceptions import (
    CODE_FEATURE_UNAVAILABLE,
    CODE_QUOTA_EXCEEDED,
    CODE_RATE_LIMITED,
    QuotaStoreUnavailableError,
    RateLimitExceededError,
)
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService
from app.services.rate_limit.store import PostgresRateLimitStore
from sqlalchemy.exc import OperationalError


def _user() -> User:
    return User(
        user_id=uuid.uuid4(),
        display_name="Quota User",
        auth_provider_id=f"uid-{uuid.uuid4()}",
    )


@pytest.fixture
def quota_service(rate_limit_enabled: PostgresRateLimitStore) -> QuotaService:
    return QuotaService(rate_limit_enabled)


async def test_per_user_quota_exceeded(quota_service, monkeypatch) -> None:
    monkeypatch.setattr(settings, "quota_cover_image_per_user", 1)
    user = _user()
    await quota_service.reserve(QuotaFeature.COVER_IMAGE, user)

    with pytest.raises(RateLimitExceededError) as caught:
        await quota_service.reserve(QuotaFeature.COVER_IMAGE, user)

    assert caught.value.code == CODE_QUOTA_EXCEEDED
    assert caught.value.scope == "cover_image"
    assert caught.value.reset_at is not None


async def test_global_cap_blocks_everyone(quota_service, monkeypatch) -> None:
    monkeypatch.setattr(settings, "quota_publish_global", 1)
    await quota_service.reserve(QuotaFeature.PUBLISH, _user())

    with pytest.raises(RateLimitExceededError) as caught:
        await quota_service.reserve(QuotaFeature.PUBLISH, _user())

    assert caught.value.code == CODE_FEATURE_UNAVAILABLE


async def test_global_cap_rejection_does_not_consume_user_quota(
    quota_service, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "quota_publish_global", 1)
    await quota_service.reserve(QuotaFeature.PUBLISH, _user())
    blocked_user = _user()

    with pytest.raises(RateLimitExceededError):
        await quota_service.reserve(QuotaFeature.PUBLISH, blocked_user)

    assert (
        await quota_service.used_today(QuotaFeature.PUBLISH, blocked_user.user_id) == 0
    )


async def test_exempt_user_bypasses_user_quota_but_not_global(
    quota_service, monkeypatch
) -> None:
    user = _user()
    monkeypatch.setattr(
        settings, "rate_limit_exempt_firebase_uids", user.auth_provider_id
    )
    monkeypatch.setattr(settings, "quota_cover_image_per_user", 1)
    monkeypatch.setattr(settings, "quota_cover_image_global", 3)

    for _ in range(3):
        await quota_service.reserve(QuotaFeature.COVER_IMAGE, user)
    with pytest.raises(RateLimitExceededError) as caught:
        await quota_service.reserve(QuotaFeature.COVER_IMAGE, user)

    assert caught.value.code == CODE_FEATURE_UNAVAILABLE


async def test_reserved_block_refunds_on_failure(quota_service) -> None:
    user = _user()

    with pytest.raises(RuntimeError):
        async with quota_service.reserved(QuotaFeature.COVER_IMAGE, user):
            raise RuntimeError("image generation failed")

    assert await quota_service.used_today(QuotaFeature.COVER_IMAGE, user.user_id) == 0


async def test_reserved_block_keeps_unit_on_success(quota_service) -> None:
    user = _user()

    async with quota_service.reserved(QuotaFeature.COVER_IMAGE, user):
        pass

    assert await quota_service.used_today(QuotaFeature.COVER_IMAGE, user.user_id) == 1


async def test_store_failure_fails_closed(quota_service, monkeypatch) -> None:
    async def _broken_reserve(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("db down"))

    monkeypatch.setattr(quota_service.store, "reserve", _broken_reserve)

    with pytest.raises(QuotaStoreUnavailableError):
        await quota_service.reserve(QuotaFeature.COVER_IMAGE, _user())


async def test_disabled_rate_limiting_skips_quota(quota_service, monkeypatch) -> None:
    monkeypatch.setattr(settings, "is_rate_limit_enabled", False)

    assert await quota_service.reserve(QuotaFeature.COVER_IMAGE, _user()) is None


async def test_account_creation_throttled_per_ip(quota_service, monkeypatch) -> None:
    monkeypatch.setattr(settings, "new_accounts_per_ip_per_day", 2)
    for _ in range(2):
        await quota_service.reserve_account_creation("198.51.100.4")

    with pytest.raises(RateLimitExceededError) as caught:
        await quota_service.reserve_account_creation("198.51.100.4")

    assert caught.value.code == CODE_RATE_LIMITED
    await quota_service.reserve_account_creation("198.51.100.5")
