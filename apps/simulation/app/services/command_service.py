from functools import partial
from uuid import NAMESPACE_URL, UUID, uuid5

from app.engine.commands.application import accept_command
from app.engine.commands.cancellation import cancel_command
from app.engine.commands.check import check_command
from app.engine.endings import require_game_not_ended
from app.engine.negotiation import require_no_open_negotiation
from app.engine.world_document import world_from_document
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.models.api_commands import AcceptCommandRequest, CommandPage
from app.models.api_orders import OrderCheckResponse
from app.models.battle_command import AcceptedCommand, Command
from app.models.battle_progress import MutationResponse, OperationGuard
from app.models.replay import AcceptCommandReplayInput, CancelCommandReplayInput
from app.repositories import command_repo, world_state_repo
from app.services.campaign_state import player_faction
from app.services.campaign_transaction import (
    CampaignTransaction,
    CampaignTransition,
    LockedCampaign,
    require_owner,
)
from psycopg import AsyncConnection


class CommandService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection
        self._transaction = CampaignTransaction(connection)

    async def accept_request(
        self, playthrough_id: UUID, user_id: UUID, request: AcceptCommandRequest
    ) -> MutationResponse:
        """Extract the canonical guard without including the command twice in the operation digest."""
        guard = OperationGuard.model_validate(request.model_dump(exclude={"command"}))
        return await self.accept(playthrough_id, user_id, guard, request.command)

    async def command_page(
        self, playthrough_id: UUID, user_id: UUID, after_id: str, limit: int
    ) -> CommandPage:
        """A full page supplies a continuation; its next page may be empty."""
        items = await self.list_commands(playthrough_id, user_id, after_id, limit)
        return CommandPage(
            items=items, next_after_id=items[-1].id if len(items) == limit else None
        )

    async def accept(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        guard: OperationGuard,
        command: Command,
    ) -> MutationResponse:
        """Commit a reserved command and its original observer-safe operation response together."""

        transition = partial(_accept_transition, user_id, guard, command)
        payload = guard.model_dump(mode="json") | {
            "command": command.model_dump(mode="json")
        }
        return await self._transaction.run(
            playthrough_id, user_id, guard, "accept_command", payload, transition
        )

    async def cancel(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        guard: OperationGuard,
        command_id: str,
    ) -> MutationResponse:
        """Remove a queued planning order and refund its points, committed with its journal step."""
        transition = partial(_cancel_transition, guard, command_id)
        payload = guard.model_dump(mode="json") | {"command_id": command_id}
        return await self._transaction.run(
            playthrough_id, user_id, guard, "cancel_command", payload, transition
        )

    async def check(
        self, playthrough_id: UUID, user_id: UUID, command: Command
    ) -> OrderCheckResponse:
        """Dry-run an order against the current world: no points charged, nothing written."""
        async with self._connection.transaction():
            playthrough = await require_owner(self._connection, playthrough_id, user_id)
            row = await world_state_repo.get_world_state(
                self._connection, playthrough_id
            )
            if row is None:
                raise PlaythroughNotFoundError()
            world = world_from_document(row.document)
            wave = world.progress.completed_waves + 1 if world.progress.phase else 0
            result = check_command(
                world,
                playthrough.scenario,
                command,
                faction_id=player_faction(world),
                expected_turn=world.clock.turn,
                expected_wave=wave,
            )
        return OrderCheckResponse(
            flag=result.flag,
            reason=result.reason,
            orders_remaining=result.orders_remaining,
        )

    async def list_commands(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        after_id: str = "",
        limit: int = command_repo.COMMAND_PAGE_DEFAULT_LIMIT,
    ) -> list[AcceptedCommand]:
        """List acceptance-ordered owner commands, default50/max200; after_id is the last returned command ID.

        The cursor is resolved within this playthrough/actor scope. Unknown and
        foreign cursors both fail422; new commands remain reachable regardless of UUID order.
        """
        async with self._connection.transaction():
            await require_owner(self._connection, playthrough_id, user_id)
            return await command_repo.list_commands(
                self._connection, playthrough_id, str(user_id), after_id, limit
            )


async def _accept_transition(
    user_id: UUID, guard: OperationGuard, command: Command, locked: LockedCampaign
) -> CampaignTransition:
    require_game_not_ended(locked.world)
    require_no_open_negotiation(locked.world)
    identity = str(
        uuid5(
            NAMESPACE_URL,
            f"{locked.world.playthrough_id}:{user_id}:{guard.operation_id}",
        )
    )
    result = accept_command(
        locked.world,
        locked.playthrough.scenario,
        command,
        command_id=identity,
        operation_id=guard.operation_id,
        actor_id=str(user_id),
        faction_id=player_faction(locked.world),
        expected_turn=guard.expected_turn,
        expected_wave=guard.expected_wave,
    )
    return CampaignTransition(
        result.world,
        events=result.events,
        accepted_command_id=result.command.id if result.command else None,
        replay_input=AcceptCommandReplayInput(
            actor_id=str(user_id), guard=guard, command=command
        ),
    )


async def _cancel_transition(
    guard: OperationGuard, command_id: str, locked: LockedCampaign
) -> CampaignTransition:
    require_game_not_ended(locked.world)
    require_no_open_negotiation(locked.world)
    world = cancel_command(
        locked.world,
        locked.playthrough.scenario,
        command_id,
        faction_id=player_faction(locked.world),
        expected_turn=guard.expected_turn,
    )
    return CampaignTransition(
        world,
        replay_input=CancelCommandReplayInput(guard=guard, command_id=command_id),
    )
