import hashlib
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.config import get_settings
from app.engine.endings import find_ending_definition
from app.engine.world_document import world_from_document
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.exceptions.base import SimulationServiceError
from app.integrations.core_api_client import sync_outcome_text
from app.models.epilogue_delivery import EpilogueDelivery
from app.models.world_state import WorldState
from app.repositories import epilogue_delivery_repo as repository
from app.repositories import playthrough_repo, summary_delivery_repo, world_state_repo
from app.services.campaign_transaction import require_owner
from app.services.epilogue_briefing import build_epilogue_briefing
from psycopg import AsyncConnection
from strategy_contracts.epilogue import (
    EpilogueBriefing,
    EpilogueClaim,
    EpilogueCompleteInput,
    EpilogueFailInput,
    EpilogueView,
)
from strategy_contracts.scenario import EndingDefinition


def _error(code: str, status_code: int = 409) -> SimulationServiceError:
    return SimulationServiceError(code.replace("_", " "), status_code, code)


def _digest(briefing: EpilogueBriefing) -> str:
    return hashlib.sha256(briefing.model_dump_json().encode()).hexdigest()


def project_epilogue(row: EpilogueDelivery) -> EpilogueView:
    return EpilogueView(
        status=row.status,
        narration=row.narration,
        error_code=row.error_code,
        is_retryable=row.status != "completed"
        and row.attempts < get_settings().summary_max_attempts,
    )


def _is_same_active_claim(row: EpilogueDelivery, claim_id: UUID) -> bool:
    return (
        row.status == "generating"
        and row.claim_id == claim_id
        and row.lease_expires_at > datetime.now(timezone.utc)
    )


def _claim_view(row: EpilogueDelivery) -> EpilogueClaim:
    return EpilogueClaim(
        epilogue=project_epilogue(row),
        briefing=row.briefing,
        input_hash=row.input_hash,
        lease_token=row.lease_token if row.status == "generating" else None,
    )


class EpilogueService:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def _ended_world(self, identity: UUID, user: UUID) -> WorldState:
        await require_owner(self.connection, identity, user)
        row = await world_state_repo.get_world_state(self.connection, identity)
        if row is None:
            raise PlaythroughNotFoundError()
        world = world_from_document(row.document)
        if world.ending is None:
            raise _error("epilogue_not_available")
        return world

    async def _ending_definition(
        self, identity: UUID, world: WorldState
    ) -> EndingDefinition | None:
        playthrough = await playthrough_repo.get_playthrough(self.connection, identity)
        if playthrough is None or world.ending is None:
            return None
        return find_ending_definition(playthrough.scenario, world.ending.ending_id)

    async def _ensure_row(self, identity: UUID, user: UUID) -> EpilogueDelivery:
        world = await self._ended_world(identity, user)
        entries = await summary_delivery_repo.completed_narrations(
            self.connection, identity
        )
        definition = await self._ending_definition(identity, world)
        briefing = build_epilogue_briefing(world, entries, definition)
        await repository.insert_if_absent(self.connection, briefing, _digest(briefing))
        row = await repository.get(self.connection, identity, should_lock=True)
        if row is None:
            raise _error("epilogue_not_available")
        return row

    async def get(self, identity: UUID, user: UUID) -> EpilogueView:
        await self._ended_world(identity, user)
        row = await repository.get(self.connection, identity)
        if row is None:
            return EpilogueView(status="pending", is_retryable=True)
        return project_epilogue(row)

    async def claim(self, identity: UUID, user: UUID, claim_id: UUID) -> EpilogueClaim:
        async with self.connection.transaction():
            row = await self._ensure_row(identity, user)
            if row.status == "completed" or _is_same_active_claim(row, claim_id):
                return _claim_view(row)
            settings = get_settings()
            claimed = await repository.claim(
                self.connection,
                identity,
                claim_id,
                uuid4(),
                settings.summary_lease_seconds,
                settings.summary_max_attempts,
            )
            if claimed is None:
                raise _error(
                    "epilogue_in_progress"
                    if row.status == "generating"
                    else "epilogue_attempts_exhausted"
                )
            return _claim_view(claimed)

    async def complete(
        self, identity: UUID, user: UUID, request: EpilogueCompleteInput
    ) -> EpilogueView:
        async with self.connection.transaction():
            row = await self._ensure_row(identity, user)
            digest = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
            if request.input_hash != row.input_hash:
                raise _error("idempotency_conflict")
            if row.status == "completed":
                return self._replayed_completion(row, request, digest)
            if not await repository.complete(
                self.connection,
                identity,
                request.lease_token,
                request.narration,
                digest,
            ):
                raise _error("stale_epilogue_lease")
            view = await self._reload(identity)
        await sync_outcome_text(identity, request.narration)
        return view

    @staticmethod
    def _replayed_completion(
        row: EpilogueDelivery, request: EpilogueCompleteInput, digest: str
    ) -> EpilogueView:
        if row.lease_token != request.lease_token or row.completion_hash != digest:
            raise _error("idempotency_conflict")
        return project_epilogue(row)

    async def fail(
        self, identity: UUID, user: UUID, request: EpilogueFailInput
    ) -> EpilogueView:
        async with self.connection.transaction():
            row = await self._ensure_row(identity, user)
            if row.status == "completed":
                return project_epilogue(row)
            if row.status == "failed" and row.lease_token == request.lease_token:
                return project_epilogue(row)
            if not await repository.fail(
                self.connection, identity, request.lease_token, request.error_code
            ):
                raise _error("stale_epilogue_lease")
            return await self._reload(identity)

    async def _reload(self, identity: UUID) -> EpilogueView:
        row = await repository.get(self.connection, identity)
        if row is None:
            raise _error("epilogue_not_available")
        return project_epilogue(row)
