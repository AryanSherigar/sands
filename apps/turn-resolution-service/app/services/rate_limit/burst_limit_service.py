"""Sliding-window burst limits per route group, keyed by user or client IP.

Fails open: if the store errors, the request proceeds and the error is logged.
Per-request throttling is an availability feature; AI spend is protected
separately by the fail-closed quota service.
"""

import uuid
from dataclasses import dataclass

import structlog
from app.services.rate_limit.client_identity import ClientIdentity
from app.services.rate_limit.exemption_service import ExemptionService
from app.services.rate_limit.policies import (
    BurstPolicy,
    KeyKind,
    ip_ceiling_policy,
    match_burst_policy,
)
from app.services.rate_limit.sliding_window import SlidingWindowDecision, decide
from app.services.rate_limit.store import (
    EVENT_RATE_LIMIT_STORE_ERROR,
    STORE_ERRORS,
    RateLimitStore,
)

logger = structlog.get_logger()

EVENT_RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


@dataclass(frozen=True)
class BurstOutcome:
    policy: BurstPolicy
    decision: SlidingWindowDecision


def _subject_key(policy: BurstPolicy, identity: ClientIdentity) -> str:
    is_user_keyed = policy.key_kind != KeyKind.IP and identity.user_id is not None
    if is_user_keyed:
        return f"burst:{policy.group}:user:{identity.user_id}"
    return f"burst:{policy.group}:ip:{identity.ip}"


class BurstLimitService:
    def __init__(self, store: RateLimitStore, exemptions: ExemptionService) -> None:
        self.store = store
        self.exemptions = exemptions

    async def check(
        self, identity: ClientIdentity, method: str, path: str
    ) -> BurstOutcome | None:
        """Return the rejecting outcome if any limit trips, else the route's own."""
        try:
            return await self._check_policies(identity, method, path)
        except STORE_ERRORS as error:
            logger.error(EVENT_RATE_LIMIT_STORE_ERROR, path=path, error=str(error))
            return None

    async def _check_policies(
        self, identity: ClientIdentity, method: str, path: str
    ) -> BurstOutcome | None:
        if identity.user_id is not None:
            ceiling = await self._hit(ip_ceiling_policy(), identity)
            if not ceiling.decision.is_allowed:
                return ceiling
        policy = match_burst_policy(method, path, identity.is_authenticated)
        if await self._is_exempt(policy, identity.user_id):
            return None
        return await self._hit(policy, identity)

    async def _is_exempt(self, policy: BurstPolicy, user_id: uuid.UUID | None) -> bool:
        if policy.key_kind == KeyKind.IP or user_id is None:
            return False
        return await self.exemptions.is_exempt_user(user_id)

    async def _hit(self, policy: BurstPolicy, identity: ClientIdentity) -> BurstOutcome:
        key = _subject_key(policy, identity)
        hit = await self.store.hit_sliding_window(key, policy.window_seconds)
        decision = decide(
            hit.previous_count,
            hit.current_count,
            hit.elapsed_seconds,
            policy.window_seconds,
            policy.limit,
        )
        if not decision.is_allowed:
            logger.warning(EVENT_RATE_LIMIT_EXCEEDED, group=policy.group, key=key)
        return BurstOutcome(policy=policy, decision=decision)
