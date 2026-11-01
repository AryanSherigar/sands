"""Daily per-user quotas and app-wide caps for AI-cost operations.

A unit is reserved before the AI call and refunded only when the call fails
on our side; validation that the user can fix happens before reserve().
Store failures fail closed: an uncounted AI call is exactly what this guards.
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import structlog
from app.config import settings
from app.db.connection import AsyncSessionFactory
from app.exceptions.rate_limit_exceptions import (
    CODE_FEATURE_UNAVAILABLE,
    CODE_QUOTA_EXCEEDED,
    LimitPolicy,
    QuotaStoreUnavailableError,
    RateLimitExceededError,
)
from app.services.rate_limit.exemption_service import (
    ExemptionService,
    get_exemption_service,
)
from app.services.rate_limit.policies import QuotaFeature, QuotaPolicy, quota_policy
from app.services.rate_limit.quota_event_recorder import QuotaEventRecorder
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

FEATURE_LABELS: dict[str, str] = {
    QuotaFeature.TURN.value: "turn",
    QuotaFeature.SCENE_IMAGE.value: "scene image",
    QuotaFeature.STRATEGY_ART.value: "strategy art",
    QuotaFeature.TTS_NARRATION.value: "voice narration",
    QuotaFeature.SPEECH_TO_TEXT.value: "voice input",
    QuotaFeature.ASSISTANT.value: "studio assistant",
}

_logged_global_caps: set[tuple[str, date]] = set()


def user_quota_key(feature: str, user_id: uuid.UUID) -> str:
    return f"quota:{feature}:user:{user_id}"


def global_quota_key(feature: str) -> str:
    return f"quota:{feature}:global"


def _next_reset(window_seconds: int) -> datetime:
    epoch_seconds = int(datetime.now(UTC).timestamp())
    window_start = epoch_seconds - epoch_seconds % window_seconds
    return datetime.fromtimestamp(window_start, tz=UTC) + timedelta(
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
        message = f"The {label} feature is unavailable for the rest of today due to high demand. It resets at 00:00 UTC."
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
    def __init__(
        self,
        store: RateLimitStore,
        exemptions: ExemptionService,
        event_recorder: QuotaEventRecorder | None = None,
    ) -> None:
        self.store = store
        self.exemptions = exemptions
        self.event_recorder = event_recorder

    async def reserve(
        self, feature: QuotaFeature, user_id: uuid.UUID
    ) -> QuotaReservation | None:
        """Take one unit of today's quota; None when rate limiting is disabled."""
        if not settings.is_rate_limit_enabled:
            return None
        policy = quota_policy(feature)
        limits = await self._limits_for(policy, user_id)
        result = await self._reserve_or_fail_closed(limits, policy)
        if result.window_start is None:
            await self._record_exceeded(policy, result.exceeded_key, user_id)
            raise self._on_exceeded(policy, result.exceeded_key, user_id)
        keys = tuple(limit.key for limit in limits)
        return QuotaReservation(self.store, keys, result.window_start)

    @asynccontextmanager
    async def reserved(
        self, feature: QuotaFeature, user_id: uuid.UUID
    ) -> AsyncIterator[QuotaReservation | None]:
        """Reserve for the body's duration, refunding if the body raises."""
        reservation = await self.reserve(feature, user_id)
        try:
            yield reservation
        except BaseException:
            if reservation is not None:
                await reservation.refund()
            raise

    async def _limits_for(
        self, policy: QuotaPolicy, user_id: uuid.UUID
    ) -> list[CounterLimit]:
        global_limit = CounterLimit(
            global_quota_key(policy.feature), policy.global_limit
        )
        try:
            is_exempt = await self.exemptions.is_exempt_user(user_id)
        except STORE_ERRORS as error:
            logger.error(
                EVENT_RATE_LIMIT_STORE_ERROR, scope=policy.feature, error=str(error)
            )
            raise QuotaStoreUnavailableError(policy.feature) from error
        if is_exempt:
            return [global_limit]
        user_limit = CounterLimit(
            user_quota_key(policy.feature, user_id), policy.per_user_limit
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

    async def _record_exceeded(
        self, policy: QuotaPolicy, exceeded_key: str | None, user_id: uuid.UUID
    ) -> None:
        if self.event_recorder is None:
            return
        is_global = exceeded_key == global_quota_key(policy.feature)
        await self.event_recorder.record_exceeded(
            user_id, policy.feature, is_global=is_global
        )

    def _on_exceeded(
        self, policy: QuotaPolicy, exceeded_key: str | None, user_id: uuid.UUID
    ) -> RateLimitExceededError:
        is_global = exceeded_key == global_quota_key(policy.feature)
        if is_global:
            _log_global_cap_once(policy.feature)
            return _exceeded_error(policy, is_global=True, limit=policy.global_limit)
        logger.warning(EVENT_QUOTA_EXCEEDED, scope=policy.feature, user_id=str(user_id))
        return _exceeded_error(policy, is_global=False, limit=policy.per_user_limit)


def get_quota_service(
    store: RateLimitStore = Depends(get_rate_limit_store),
    exemptions: ExemptionService = Depends(get_exemption_service),
) -> QuotaService:
    return QuotaService(store, exemptions, QuotaEventRecorder(AsyncSessionFactory))
