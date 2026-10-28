"""Daily per-user quotas and app-wide caps for AI-cost operations.

A unit is reserved before the AI call and refunded only when the call fails
on our side; validation that the user can fix happens before reserve().
Store failures fail closed: an uncounted AI call is exactly what this guards.
"""

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import structlog
from app.config import settings
from app.db.models.user import User
from app.exceptions.rate_limit_exceptions import (
    CODE_FEATURE_UNAVAILABLE,
    CODE_QUOTA_EXCEEDED,
    CODE_RATE_LIMITED,
    LimitPolicy,
    QuotaStoreUnavailableError,
    RateLimitExceededError,
)
from app.services.rate_limit.policies import (
    SECONDS_PER_DAY,
    QuotaFeature,
    QuotaPolicy,
    quota_policy,
)
from app.services.rate_limit.store import (
    EVENT_RATE_LIMIT_STORE_ERROR,
    STORE_ERRORS,
    CounterLimit,
    RateLimitStore,
    ReserveResult,
    get_rate_limit_store,
)
from fastapi import Depends

logger = structlog.get_logger()

EVENT_QUOTA_EXCEEDED = "quota_exceeded"
EVENT_GLOBAL_CAP_REACHED = "global_cap_reached"
EVENT_QUOTA_REFUND_FAILED = "quota_refund_failed"
ACCOUNT_CREATION_SCOPE = "account_creation"

FEATURE_LABELS: dict[str, str] = {
    QuotaFeature.COVER_IMAGE.value: "cover image generation",
    QuotaFeature.MUSIC_GENERATION.value: "music generation",
    QuotaFeature.PUBLISH.value: "publishing",
}

_logged_global_caps: set[tuple[str, date]] = set()


def user_quota_key(feature: str, user_id: object) -> str:
    return f"quota:{feature}:user:{user_id}"


def global_quota_key(feature: str) -> str:
    return f"quota:{feature}:global"


def account_creation_key(ip: str) -> str:
    return f"acct:ip:{ip}"


def window_start_for(moment: datetime, window_seconds: int) -> datetime:
    epoch_seconds = int(moment.timestamp())
    return datetime.fromtimestamp(
        epoch_seconds - epoch_seconds % window_seconds, tz=UTC
    )


def _next_reset(window_seconds: int) -> datetime:
    return window_start_for(datetime.now(UTC), window_seconds) + timedelta(
        seconds=window_seconds
    )


def _seconds_until(moment: datetime) -> int:
    return max(1, int((moment - datetime.now(UTC)).total_seconds()))


@dataclass
class QuotaReservation:
    store: RateLimitStore
    keys: tuple[str, ...]
    window_start: datetime
    is_refunded: bool = field(default=False)

    async def refund(self) -> None:
        if self.is_refunded:
            return
        self.is_refunded = True
        try:
            await self.store.refund(self.keys, self.window_start)
        except STORE_ERRORS as error:
            logger.error(EVENT_QUOTA_REFUND_FAILED, keys=self.keys, error=str(error))


def _exceeded_error(
    policy: QuotaPolicy, is_global: bool, limit: int
) -> RateLimitExceededError:
    reset_at = _next_reset(policy.window_seconds)
    label = FEATURE_LABELS.get(policy.feature, policy.feature)
    if is_global:
        message = f"{label.capitalize()} is unavailable for the rest of today due to high demand. It resets at 00:00 UTC."
        code = CODE_FEATURE_UNAVAILABLE
    else:
        message = f"You've reached today's {label} limit. It resets at 00:00 UTC."
        code = CODE_QUOTA_EXCEEDED
    return RateLimitExceededError(
        message,
        code=code,
        scope=policy.feature,
        reset_at=reset_at,
        retry_after_seconds=_seconds_until(reset_at),
        policy=LimitPolicy(limit=limit, window_seconds=policy.window_seconds),
    )


def _log_global_cap_once(feature: str) -> None:
    marker = (feature, datetime.now(UTC).date())
    if marker in _logged_global_caps:
        return
    _logged_global_caps.add(marker)
    logger.error(EVENT_GLOBAL_CAP_REACHED, feature=feature)


class QuotaService:
    def __init__(self, store: RateLimitStore) -> None:
        self.store = store

    async def reserve(
        self, feature: QuotaFeature, user: User
    ) -> QuotaReservation | None:
        """Take one unit of today's quota; None when rate limiting is disabled."""
        if not settings.is_rate_limit_enabled:
            return None
        policy = quota_policy(feature)
        limits = self._limits_for(policy, user)
        result = await self._reserve_or_fail_closed(limits, policy)
        if result.window_start is None:
            raise self._on_exceeded(policy, result.exceeded_key, user)
        keys = tuple(limit.key for limit in limits)
        return QuotaReservation(self.store, keys, result.window_start)

    @asynccontextmanager
    async def reserved(
        self, feature: QuotaFeature, user: User
    ) -> AsyncIterator[QuotaReservation | None]:
        """Reserve for the body's duration, refunding if the body raises."""
        reservation = await self.reserve(feature, user)
        try:
            yield reservation
        except BaseException:
            if reservation is not None:
                await reservation.refund()
            raise

    async def refund_for(
        self, feature: QuotaFeature, user_id: object, occurred_at: datetime
    ) -> None:
        """Refund a unit reserved earlier by another request (background jobs)."""
        if not settings.is_rate_limit_enabled:
            return
        policy = quota_policy(feature)
        keys = (
            user_quota_key(policy.feature, user_id),
            global_quota_key(policy.feature),
        )
        window_start = window_start_for(occurred_at, policy.window_seconds)
        await QuotaReservation(self.store, keys, window_start).refund()

    async def used_today(self, feature: QuotaFeature, user_id: object) -> int:
        if not settings.is_rate_limit_enabled:
            return 0
        key = user_quota_key(feature.value, user_id)
        try:
            return await self.store.current_count(key, SECONDS_PER_DAY)
        except STORE_ERRORS as error:
            logger.error(EVENT_RATE_LIMIT_STORE_ERROR, key=key, error=str(error))
            raise QuotaStoreUnavailableError(feature.value) from error

    async def reserve_account_creation(self, ip: str) -> None:
        if not settings.is_rate_limit_enabled:
            return
        policy = QuotaPolicy(
            ACCOUNT_CREATION_SCOPE, settings.new_accounts_per_ip_per_day, 0
        )
        limits = [CounterLimit(account_creation_key(ip), policy.per_user_limit)]
        result = await self._reserve_or_fail_closed(limits, policy)
        if result.window_start is None:
            logger.warning(EVENT_QUOTA_EXCEEDED, scope=ACCOUNT_CREATION_SCOPE, ip=ip)
            reset_at = _next_reset(policy.window_seconds)
            raise RateLimitExceededError(
                "Too many new accounts have been created from this network today. Please try again tomorrow.",
                code=CODE_RATE_LIMITED,
                scope=ACCOUNT_CREATION_SCOPE,
                reset_at=reset_at,
                retry_after_seconds=_seconds_until(reset_at),
                policy=LimitPolicy(policy.per_user_limit, policy.window_seconds),
            )

    def _limits_for(self, policy: QuotaPolicy, user: User) -> list[CounterLimit]:
        global_limit = CounterLimit(
            global_quota_key(policy.feature), policy.global_limit
        )
        if user.auth_provider_id in settings.exempt_firebase_uids:
            return [global_limit]
        user_limit = CounterLimit(
            user_quota_key(policy.feature, user.user_id), policy.per_user_limit
        )
        return [user_limit, global_limit]

    async def _reserve_or_fail_closed(
        self, limits: list[CounterLimit], policy: QuotaPolicy
    ) -> ReserveResult:
        try:
            return await self.store.reserve(limits, policy.window_seconds)
        except STORE_ERRORS as error:
            logger.error(
                EVENT_RATE_LIMIT_STORE_ERROR, scope=policy.feature, error=str(error)
            )
            raise QuotaStoreUnavailableError(policy.feature) from error

    def _on_exceeded(
        self, policy: QuotaPolicy, exceeded_key: str | None, user: User
    ) -> RateLimitExceededError:
        is_global = exceeded_key == global_quota_key(policy.feature)
        if is_global:
            _log_global_cap_once(policy.feature)
            return _exceeded_error(policy, is_global=True, limit=policy.global_limit)
        logger.warning(
            EVENT_QUOTA_EXCEEDED, scope=policy.feature, user_id=str(user.user_id)
        )
        return _exceeded_error(policy, is_global=False, limit=policy.per_user_limit)


def quota_scope(
    quota_service: QuotaService | None, feature: QuotaFeature, user: User
) -> AbstractAsyncContextManager[QuotaReservation | None]:
    """Reserve around a block, or do nothing when no quota service is wired."""
    if quota_service is None:
        return nullcontext(None)
    return quota_service.reserved(feature, user)


def get_quota_service(
    store: RateLimitStore = Depends(get_rate_limit_store),
) -> QuotaService:
    return QuotaService(store)
