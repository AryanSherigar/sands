"""Per-turn quota bookkeeping threaded through pipeline.py.

The turn itself must fit today's quota or the request is refused before any
SSE byte is sent. Scene images and voice narration are optional extras: when
their quota is spent (or the store is down) they are skipped and the turn
still narrates, carrying a notice for the client instead.
"""

import uuid
from dataclasses import dataclass

from app.exceptions.rate_limit_exceptions import (
    QuotaStoreUnavailableError,
    RateLimitExceededError,
)
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaReservation, QuotaService


@dataclass(frozen=True)
class ExtraReservation:
    reservation: QuotaReservation | None
    denial: RateLimitExceededError | QuotaStoreUnavailableError | None

    @property
    def is_allowed(self) -> bool:
        return self.denial is None

    async def refund(self) -> None:
        if self.reservation is not None:
            await self.reservation.refund()


class TurnQuota:
    def __init__(self, quota_service: QuotaService | None, user_id: uuid.UUID) -> None:
        self._quota_service = quota_service
        self._user_id = user_id
        self._turn_reservation: QuotaReservation | None = None

    async def reserve_turn(self) -> None:
        if self._quota_service is None:
            return
        self._turn_reservation = await self._quota_service.reserve(
            QuotaFeature.TURN, self._user_id
        )

    async def refund_turn(self) -> None:
        if self._turn_reservation is not None:
            await self._turn_reservation.refund()

    async def reserve_extra(self, feature: QuotaFeature) -> ExtraReservation:
        if self._quota_service is None:
            return ExtraReservation(reservation=None, denial=None)
        try:
            reservation = await self._quota_service.reserve(feature, self._user_id)
        except (RateLimitExceededError, QuotaStoreUnavailableError) as denial:
            return ExtraReservation(reservation=None, denial=denial)
        return ExtraReservation(reservation=reservation, denial=None)
