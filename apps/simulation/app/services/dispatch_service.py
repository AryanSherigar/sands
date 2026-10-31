from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.config import get_settings
from app.exceptions.base import SimulationServiceError
from app.models.dispatch_delivery import DispatchDelivery
from app.repositories import dispatch_delivery_repo as repository
from app.services.campaign_transaction import require_owner
from psycopg import AsyncConnection
from strategy_contracts.agents import (
    DispatchClaim,
    DispatchCompleteInput,
    DispatchFailInput,
    DispatchView,
)


def _error(code: str) -> SimulationServiceError:
    return SimulationServiceError(code.replace("_", " "), 409, code)


def _is_same_active_claim(row: DispatchDelivery, claim_id: UUID) -> bool:
    return (
        row.status == "generating"
        and row.claim_id == claim_id
        and row.lease_expires_at is not None
        and row.lease_expires_at > datetime.now(timezone.utc)
    )


def project_dispatch(row: DispatchDelivery) -> DispatchView:
    briefing = row.briefing
    return DispatchView(
        rumor_id=row.rumor_id,
        turn=row.turn,
        agent=briefing.agent,
        about_faction_id=briefing.about_faction_id,
        topic=briefing.topic,
        status=row.status,
        narration=row.narration,
        fallback_line_key=f"{briefing.topic.value}.{briefing.reported_band.value}",
        error_code=row.error_code,
    )


class DispatchService:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def _owned(
        self, identity: UUID, user: UUID, rumor_id: str, should_lock: bool = False
    ) -> DispatchDelivery:
        await require_owner(self.connection, identity, user)
        row = await repository.get(self.connection, identity, rumor_id, should_lock)
        if row is None:
            raise SimulationServiceError("Dispatch not found", 404, "not_found")
        return row

    async def get(self, identity: UUID, user: UUID, rumor_id: str) -> DispatchView:
        return project_dispatch(await self._owned(identity, user, rumor_id))

    async def page(self, identity: UUID, user: UUID, limit: int) -> list[DispatchView]:
        await require_owner(self.connection, identity, user)
        rows = await repository.list_page(self.connection, identity, limit)
        return [project_dispatch(row) for row in rows]

    async def claim(
        self, identity: UUID, user: UUID, rumor_id: str, claim_id: UUID
    ) -> DispatchClaim:
        async with self.connection.transaction():
            row = await self._owned(identity, user, rumor_id, True)
            if row.status == "completed":
                return DispatchClaim(dispatch=project_dispatch(row))
            if _is_same_active_claim(row, claim_id):
                return self._claim_of(row, row.lease_token)
            return await self._take_lease(row, claim_id)

    @staticmethod
    def _claim_of(row: DispatchDelivery, lease_token: UUID | None) -> DispatchClaim:
        return DispatchClaim(
            dispatch=project_dispatch(row),
            briefing=row.briefing,
            lease_token=lease_token,
        )

    async def _take_lease(self, row: DispatchDelivery, claim_id: UUID) -> DispatchClaim:
        settings = get_settings()
        claimed = await repository.claim(
            self.connection,
            row.playthrough_id,
            row.rumor_id,
            claim_id,
            uuid4(),
            settings.dispatch_lease_seconds,
            settings.dispatch_max_attempts,
        )
        if claimed is None:
            raise _error(
                "dispatch_in_progress"
                if row.status == "generating"
                else "dispatch_attempts_exhausted"
            )
        return self._claim_of(claimed, claimed.lease_token)

    async def complete(
        self,
        identity: UUID,
        user: UUID,
        rumor_id: str,
        request: DispatchCompleteInput,
    ) -> DispatchView:
        async with self.connection.transaction():
            row = await self._owned(identity, user, rumor_id, True)
            if row.status == "completed":
                return self._replayed_completion(row, request)
            is_saved = await repository.complete(
                self.connection,
                identity,
                rumor_id,
                request.lease_token,
                request.narration,
            )
            if not is_saved:
                raise _error("stale_dispatch_lease")
            return await self.get(identity, user, rumor_id)

    @staticmethod
    def _replayed_completion(
        row: DispatchDelivery, request: DispatchCompleteInput
    ) -> DispatchView:
        if row.lease_token != request.lease_token or row.narration != request.narration:
            raise _error("idempotency_conflict")
        return project_dispatch(row)

    async def fail(
        self,
        identity: UUID,
        user: UUID,
        rumor_id: str,
        request: DispatchFailInput,
    ) -> DispatchView:
        async with self.connection.transaction():
            row = await self._owned(identity, user, rumor_id, True)
            if row.status == "completed" or (
                row.status == "failed" and row.lease_token == request.lease_token
            ):
                return project_dispatch(row)
            is_recorded = await repository.fail(
                self.connection,
                identity,
                rumor_id,
                request.lease_token,
                request.error_code,
            )
            if not is_recorded:
                raise _error("stale_dispatch_lease")
            return await self.get(identity, user, rumor_id)
