from uuid import UUID, uuid4

from app.engine.hashing import world_hash
from app.engine.proclamations.constants import PROCLAMATION_MANDATE_COST
from app.engine.proclamations.lifecycle import apply_proclamation_enactment
from app.engine.proclamations.stances import evaluate_minister_stances
from app.engine.world_document import world_from_document
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_faction import FactionState
from app.models.world_state import WorldState
from app.repositories import world_state_repo
from app.services.campaign_transaction import require_owner
from psycopg import AsyncConnection
from strategy_contracts.proclamation import (
    ActiveProclamation,
    ProclamationDraft,
    ProclamationScenePackage,
)


def _get_player_faction(world: WorldState) -> FactionState | None:
    return next((f for f in world.factions.values() if f.is_player), None)


def _validate_convene_preconditions(
    world: WorldState, is_rescinding_previous: bool
) -> None:
    player = _get_player_faction(world)
    if player is None or player.orders_remaining < PROCLAMATION_MANDATE_COST:
        raise CampaignProgressError(
            "Insufficient Royal Mandates (2 required)",
            "insufficient_mandates",
            400,
        )
    if (
        world.active_proclamation is not None
        and world.active_proclamation.remaining_turns > 0
        and not is_rescinding_previous
    ):
        raise CampaignProgressError(
            "An active proclamation is already in effect. Must rescind previous.",
            "active_proclamation_conflict",
            400,
        )


class ProclamationSceneService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def convene_council(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        draft: ProclamationDraft,
        is_rescinding_previous: bool = False,
    ) -> ProclamationScenePackage:
        async with self._connection.transaction():
            await require_owner(self._connection, playthrough_id, user_id)
            row = await world_state_repo.get_world_state(
                self._connection, playthrough_id
            )
            if row is None:
                raise PlaythroughNotFoundError()
            world = world_from_document(row.document)
            _validate_convene_preconditions(world, is_rescinding_previous)
            ministers = evaluate_minister_stances(world, draft)
            return ProclamationScenePackage(
                scene_id=str(uuid4()),
                draft=draft,
                ministers=ministers,
                exchange_cap=6,
                is_rescinding_previous=is_rescinding_previous,
            )

    async def decide_proclamation(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        draft: ProclamationDraft,
        verdict: str,
        is_rescinding_previous: bool = False,
    ) -> ActiveProclamation:
        async with self._connection.transaction():
            await require_owner(self._connection, playthrough_id, user_id)
            row = await world_state_repo.get_world_state(
                self._connection, playthrough_id, should_lock=True
            )
            if row is None:
                raise PlaythroughNotFoundError()
            world = world_from_document(row.document)
            _validate_convene_preconditions(world, is_rescinding_previous)
            player = _get_player_faction(world)
            if player is not None:
                player.orders_remaining -= PROCLAMATION_MANDATE_COST
            active = apply_proclamation_enactment(
                world,
                draft,
                is_rescinding=is_rescinding_previous,
                is_compromise=(verdict == "compromise"),
            )
            digest = world_hash(world)
            await world_state_repo.update_world_state(
                self._connection,
                playthrough_id,
                row.row_version,
                world.schema_version,
                world.clock.turn,
                digest,
                world.model_dump(mode="json"),
            )
            return active
