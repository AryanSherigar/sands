from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.config import get_settings
from app.exceptions.base import SimulationServiceError
from app.models.art_delivery import ArtDelivery
from app.repositories import art_delivery_repo as repository
from app.repositories import summary_delivery_repo
from app.services.art_briefing import (
    chronicle_briefing,
    event_briefing,
    uprising_briefing,
)
from app.services.campaign_transaction import require_owner
from app.services.world_view_service import WorldViewService
from psycopg import AsyncConnection
from strategy_contracts.art import (
    ArtBriefing,
    ArtClaim,
    ArtCompleteInput,
    ArtFailInput,
    ArtKind,
    ArtView,
)


def _error(code: str) -> SimulationServiceError:
    return SimulationServiceError(code.replace("_", " "), 409, code)


def _not_found() -> SimulationServiceError:
    return SimulationServiceError("Art item not found", 404, "not_found")


def project_art(row: ArtDelivery) -> ArtView:
    return ArtView(
        kind=row.kind,
        item_id=row.item_id,
        status=row.status,
        art_url=row.art_url,
        error_code=row.error_code,
        is_retryable=row.status != "completed"
        and row.attempts < get_settings().art_max_attempts,
    )


def _is_same_active_claim(row: ArtDelivery, claim_id: UUID) -> bool:
    return (
        row.status == "generating"
        and row.claim_id == claim_id
        and row.lease_expires_at is not None
        and row.lease_expires_at > datetime.now(timezone.utc)
    )


class ArtService:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def _owned_row(
        self, identity: UUID, user: UUID, kind: ArtKind, item_id: str
    ) -> ArtDelivery:
        await require_owner(self.connection, identity, user)
        row = await repository.get(self.connection, identity, kind, item_id, True)
        if row is None:
            raise _not_found()
        return row

    async def _briefing(
        self, identity: UUID, user: UUID, kind: ArtKind, item_id: str
    ) -> ArtBriefing:
        if kind == "chronicle":
            return await self._chronicle(identity, item_id)
        world = await WorldViewService(self.connection).load_world(identity, user)
        if kind == "event":
            event = next((e for e in world.pending_events if e.id == item_id), None)
            if event is not None:
                return event_briefing(event)
        else:
            uprising = next((u for u in world.uprisings if u.id == item_id), None)
            if uprising is not None:
                return uprising_briefing(uprising)
        raise _not_found()

    async def _chronicle(self, identity: UUID, item_id: str) -> ArtBriefing:
        try:
            summary_id = UUID(item_id)
        except ValueError as error:
            raise _not_found() from error
        row = await summary_delivery_repo.get(self.connection, identity, summary_id)
        if row is None:
            raise _not_found()
        return chronicle_briefing(row.briefing)

    async def claim(
        self, identity: UUID, user: UUID, kind: ArtKind, item_id: str, claim_id: UUID
    ) -> ArtClaim:
        async with self.connection.transaction():
            await require_owner(self.connection, identity, user)
            row = await repository.get(self.connection, identity, kind, item_id, True)
            if row is not None and row.status == "completed":
                return ArtClaim(art=project_art(row))
            briefing = await self._briefing(identity, user, kind, item_id)
            if row is None:
                await repository.ensure_row(self.connection, identity, kind, item_id)
                row = await repository.get(
                    self.connection, identity, kind, item_id, True
                )
            assert row is not None
            if _is_same_active_claim(row, claim_id):
                return ArtClaim(
                    art=project_art(row), briefing=briefing, lease_token=row.lease_token
                )
            return await self._take_lease(row, briefing, claim_id)

    async def _take_lease(
        self, row: ArtDelivery, briefing: ArtBriefing, claim_id: UUID
    ) -> ArtClaim:
        settings = get_settings()
        claimed = await repository.claim(
            self.connection,
            row.playthrough_id,
            row.kind,
            row.item_id,
            claim_id,
            uuid4(),
            settings.art_lease_seconds,
            settings.art_max_attempts,
        )
        if claimed is None:
            raise _error(
                "art_in_progress"
                if row.status == "generating"
                else "art_attempts_exhausted"
            )
        return ArtClaim(
            art=project_art(claimed), briefing=briefing, lease_token=claimed.lease_token
        )

    async def complete(
        self,
        identity: UUID,
        user: UUID,
        kind: ArtKind,
        item_id: str,
        request: ArtCompleteInput,
    ) -> ArtView:
        async with self.connection.transaction():
            row = await self._owned_row(identity, user, kind, item_id)
            if row.status == "completed":
                if (
                    row.lease_token != request.lease_token
                    or row.art_url != request.art_url
                ):
                    raise _error("idempotency_conflict")
                return project_art(row)
            is_saved = await repository.complete(
                self.connection,
                identity,
                kind,
                item_id,
                request.lease_token,
                request.art_url,
            )
            if not is_saved:
                raise _error("stale_art_lease")
            return project_art(await self._owned_row(identity, user, kind, item_id))

    async def fail(
        self,
        identity: UUID,
        user: UUID,
        kind: ArtKind,
        item_id: str,
        request: ArtFailInput,
    ) -> ArtView:
        async with self.connection.transaction():
            row = await self._owned_row(identity, user, kind, item_id)
            if row.status == "completed":
                return project_art(row)
            if row.status == "failed" and row.lease_token == request.lease_token:
                return project_art(row)
            is_recorded = await repository.fail(
                self.connection,
                identity,
                kind,
                item_id,
                request.lease_token,
                request.error_code,
            )
            if not is_recorded:
                raise _error("stale_art_lease")
            return project_art(await self._owned_row(identity, user, kind, item_id))
