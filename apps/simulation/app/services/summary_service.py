import hashlib
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.config import get_settings
from app.exceptions.base import SimulationServiceError
from app.models.summary_delivery import SummaryDelivery
from app.repositories import summary_delivery_repo as repository
from app.services.campaign_transaction import require_owner
from psycopg import AsyncConnection
from strategy_contracts.summary import (
    SummaryClaim,
    SummaryCompleteInput,
    SummaryFailInput,
    SummaryPage,
    SummaryView,
)


def _error(code: str) -> SimulationServiceError:
    return SimulationServiceError(code.replace("_", " "), 409, code)


def project_summary(row: SummaryDelivery) -> SummaryView:
    return SummaryView(
        summary_id=row.summary_id,
        requested_turn=row.briefing.requested_turn,
        trigger=row.briefing.trigger,
        status=row.status,
        narration=row.narration,
        error_code=row.error_code,
        is_retryable=row.status != "completed"
        and row.attempts < get_settings().summary_max_attempts,
        region_ids=sorted(
            {region for fact in row.briefing.facts for region in fact.region_ids}
        ),
    )


class SummaryService:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def _owned(
        self, identity: UUID, user: UUID, summary: UUID, should_lock: bool = False
    ) -> SummaryDelivery:
        await require_owner(self.connection, identity, user)
        row = await repository.get(self.connection, identity, summary, should_lock)
        if row is None:
            raise SimulationServiceError("Summary not found", 404, "not_found")
        return row

    async def get(self, identity: UUID, user: UUID, summary: UUID) -> SummaryView:
        return project_summary(await self._owned(identity, user, summary))

    async def page(
        self, identity: UUID, user: UUID, after: UUID | None, limit: int
    ) -> SummaryPage:
        await require_owner(self.connection, identity, user)
        if after is not None:
            await self._owned(identity, user, after)
        rows = await repository.page(self.connection, identity, after, limit + 1)
        return SummaryPage(
            items=[project_summary(row) for row in rows[:limit]],
            next_after_id=rows[limit - 1].summary_id if len(rows) > limit else None,
        )

    async def claim(
        self, identity: UUID, user: UUID, summary: UUID, claim_id: UUID
    ) -> SummaryClaim:
        async with self.connection.transaction():
            row = await self._owned(identity, user, summary, should_lock=True)
            if row.status == "completed" or _same_active_claim(row, claim_id):
                return _claim_view(row)
            settings = get_settings()
            claimed = await repository.claim(
                self.connection,
                identity,
                summary,
                claim_id,
                uuid4(),
                settings.summary_lease_seconds,
                settings.summary_max_attempts,
            )
            if claimed is None:
                raise _error(
                    "summary_in_progress"
                    if row.status == "generating"
                    else "summary_attempts_exhausted"
                )
            return _claim_view(claimed)

    async def complete(
        self, identity: UUID, user: UUID, summary: UUID, request: SummaryCompleteInput
    ) -> SummaryView:
        async with self.connection.transaction():
            row = await self._owned(identity, user, summary, should_lock=True)
            digest = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
            if request.input_hash != row.input_hash:
                raise _error("idempotency_conflict")
            if row.status == "completed":
                if (
                    row.lease_token != request.lease_token
                    or row.completion_hash != digest
                ):
                    raise _error("idempotency_conflict")
                return project_summary(row)
            if not await repository.complete(
                self.connection,
                identity,
                summary,
                request.lease_token,
                request.narration,
                digest,
            ):
                raise _error("stale_summary_lease")
            return project_summary(await self._owned(identity, user, summary))

    async def fail(
        self, identity: UUID, user: UUID, summary: UUID, request: SummaryFailInput
    ) -> SummaryView:
        async with self.connection.transaction():
            row = await self._owned(identity, user, summary, should_lock=True)
            if row.status == "completed":
                return project_summary(row)
            if row.status == "failed" and row.lease_token == request.lease_token:
                return project_summary(row)
            if not await repository.fail(
                self.connection,
                identity,
                summary,
                request.lease_token,
                request.error_code,
            ):
                raise _error("stale_summary_lease")
            return project_summary(await self._owned(identity, user, summary))


def _same_active_claim(row: SummaryDelivery, claim_id: UUID) -> bool:
    return (
        row.status == "generating"
        and row.claim_id == claim_id
        and row.lease_expires_at > datetime.now(timezone.utc)
    )


def _claim_view(row: SummaryDelivery) -> SummaryClaim:
    return SummaryClaim(
        summary=project_summary(row),
        briefing=row.briefing,
        input_hash=row.input_hash,
        lease_token=row.lease_token if row.status == "generating" else None,
    )
