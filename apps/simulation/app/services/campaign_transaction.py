from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import UUID

from app.engine.hashing import world_hash
from app.engine.phases import ScenePause
from app.engine.pipeline import TurnResult
from app.engine.world_document import world_from_document
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import AcceptedCommand
from app.models.battle_progress import MutationResponse, OperationGuard
from app.models.persistence import PlaythroughRow, WorldStateRow
from app.models.replay import ReplayInput, ReplayStep
from app.models.world_battle import ExchangeReceipt
from app.models.world_events import EventLogEntry, TurnStatus
from app.models.world_state import CounterKind, WorldState
from app.repositories import (
    battle_exchange_repo,
    command_repo,
    event_log_repo,
    operation_repo,
    playthrough_repo,
    replay_step_repo,
    turn_hash_repo,
    world_snapshot_repo,
    world_state_repo,
)
from app.services.campaign_state import mutation_response, project_state, request_hash
from app.services.economy_scene import persist_pause
from app.services.summary_materialization import persist_summary_requests
from psycopg import AsyncConnection


@dataclass(frozen=True)
class LockedCampaign:
    playthrough: PlaythroughRow
    row: WorldStateRow
    world: WorldState


@dataclass
class CampaignTransition:
    world: WorldState
    events: list[EventLogEntry] = field(default_factory=list)
    receipts: list[ExchangeReceipt] = field(default_factory=list)
    accepted_command_id: str | None = None
    is_complete: bool = False
    pause: ScenePause | None = None
    replay_input: ReplayInput | None = None


TransitionFunction = Callable[[LockedCampaign], Awaitable[CampaignTransition]]


def from_turn(
    result: TurnResult, receipts: list[ExchangeReceipt] | None = None
) -> CampaignTransition:
    return CampaignTransition(
        result.world,
        result.events,
        receipts if receipts is not None else result.receipts,
        is_complete=result.status == TurnStatus.RESOLVED,
        pause=result.pause,
    )


async def require_owner(
    connection: AsyncConnection, playthrough_id: UUID, user_id: UUID
) -> PlaythroughRow:
    row = await playthrough_repo.get_playthrough(connection, playthrough_id)
    if row is None or row.owner_user_id != user_id:
        raise PlaythroughNotFoundError()
    return row


async def replay_operation(
    connection: AsyncConnection,
    playthrough_id: UUID,
    actor_id: str,
    operation_id: str,
    digest: str,
) -> MutationResponse | None:
    row = await operation_repo.get_operation(
        connection, playthrough_id, actor_id, operation_id
    )
    if row is None:
        return None
    if row.request_hash != digest:
        raise CommandError("operation identity conflicts", "idempotency_conflict")
    return row.response


def _cursor_wave(world: WorldState) -> int:
    if world.progress.waiting_reason in (
        "awaiting_commands",
        "awaiting_battle_decision",
    ):
        return world.progress.completed_waves + 1
    return world.progress.completed_waves


def current_guard(
    world: WorldState, row: WorldStateRow, operation_id: str
) -> OperationGuard:
    return OperationGuard(
        operation_id=operation_id,
        expected_world_version=row.row_version,
        expected_turn=world.clock.turn,
        expected_wave=_cursor_wave(world),
    )


def require_cursor(
    world: WorldState, row: WorldStateRow, guard: OperationGuard
) -> None:
    current = current_guard(world, row, guard.operation_id)
    if (
        current.expected_world_version,
        current.expected_turn,
        current.expected_wave,
    ) != (guard.expected_world_version, guard.expected_turn, guard.expected_wave):
        raise CommandError("stale world or campaign cursor", "stale_cursor")


class CampaignTransaction:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def run(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        guard: OperationGuard,
        route_kind: str,
        payload: dict[str, object],
        transition: TransitionFunction,
    ) -> MutationResponse:
        digest = request_hash(route_kind, payload)
        async with self.connection.transaction():
            playthrough = await require_owner(self.connection, playthrough_id, user_id)
            previous = await replay_operation(
                self.connection,
                playthrough_id,
                str(user_id),
                guard.operation_id,
                digest,
            )
            if previous is not None:
                return previous
            return await self._locked(
                playthrough, user_id, guard, route_kind, digest, transition
            )

    async def _locked(
        self,
        playthrough: PlaythroughRow,
        user_id: UUID,
        guard: OperationGuard,
        route_kind: str,
        digest: str,
        transition: TransitionFunction,
    ) -> MutationResponse:
        identity = playthrough.playthrough_id
        row = await world_state_repo.get_world_state(
            self.connection, identity, should_lock=True
        )
        previous = await replay_operation(
            self.connection, identity, str(user_id), guard.operation_id, digest
        )
        if previous is not None:
            return previous
        world = checked_world(row, guard)
        return await self._apply(
            LockedCampaign(playthrough, row, world),
            user_id,
            guard.operation_id,
            route_kind,
            digest,
            transition,
        )

    async def _apply(
        self,
        locked: LockedCampaign,
        user_id: UUID,
        operation_id: str,
        route_kind: str,
        digest: str,
        transition: TransitionFunction,
    ) -> MutationResponse:
        result = await transition(locked)
        response = await self._persist(locked, operation_id, result)
        await operation_repo.insert_operation(
            self.connection,
            locked.world.playthrough_id,
            str(user_id),
            digest,
            route_kind,
            response,
            result.world.counters.get(CounterKind.EVENT_SEQ, 0),
        )
        return response

    async def _persist(
        self,
        locked: LockedCampaign,
        operation_id: str,
        result: CampaignTransition,
    ) -> MutationResponse:
        world = result.world
        await persist_pause(self.connection, world, result.pause, operation_id)
        digest = world_hash(world)
        await persist_evidence(self.connection, result, locked.world)
        version = await persist_current_world(
            self.connection, locked.row.row_version, world, digest
        )
        await persist_replay_step(
            self.connection, locked, operation_id, result.replay_input, digest
        )
        if result.is_complete:
            await persist_completed_turn(self.connection, world, digest)
        state = project_state(
            world, locked.playthrough.scenario, version, digest, result.is_complete
        )
        return mutation_response(state, operation_id, result.accepted_command_id)


async def persist_completed_turn(
    connection: AsyncConnection, world: WorldState, digest: str
) -> None:
    await world_snapshot_repo.insert_snapshot(
        connection,
        world.playthrough_id,
        world.clock.turn,
        world.schema_version,
        digest,
        world.model_dump(mode="json"),
    )
    await turn_hash_repo.insert_turn_hash(
        connection, world.playthrough_id, world.clock.turn, digest
    )


async def persist_evidence(
    connection: AsyncConnection, result: CampaignTransition, previous: WorldState
) -> None:
    identity = result.world.playthrough_id
    await command_repo.save_commands(
        connection, identity, changed_commands(previous, result.world)
    )
    await command_repo.delete_commands(
        connection, identity, removed_command_ids(previous, result.world)
    )
    await event_log_repo.append_events(connection, identity, result.events)
    await persist_summary_requests(connection, result.world, previous)
    await battle_exchange_repo.append_exchanges(connection, identity, result.receipts)


async def persist_current_world(
    connection: AsyncConnection, expected_version: int, world: WorldState, digest: str
) -> int:
    version = await world_state_repo.update_world_state(
        connection,
        world.playthrough_id,
        expected_version,
        world.schema_version,
        world.clock.turn,
        digest,
        world.model_dump(mode="json"),
    )
    if version is None:
        raise CommandError("world revision conflicts", "stale_version")
    return version


async def persist_replay_step(
    connection: AsyncConnection,
    locked: LockedCampaign,
    operation_id: str,
    replay_input: ReplayInput | None,
    after_hash: str,
) -> None:
    if replay_input is None:
        raise RuntimeError("campaign transition is missing replay input")
    step = ReplayStep(
        playthrough_id=locked.world.playthrough_id,
        sequence=await replay_step_repo.next_sequence(
            connection, locked.world.playthrough_id
        ),
        operation_id=operation_id,
        kind=replay_input.kind,
        input=replay_input,
        before_hash=locked.row.world_hash,
        after_hash=after_hash,
        turn=locked.world.clock.turn,
        wave=locked.world.progress.completed_waves,
    )
    await replay_step_repo.insert_step(connection, step)


def checked_world(row: WorldStateRow | None, guard: OperationGuard) -> WorldState:
    if row is None:
        raise PlaythroughNotFoundError()
    world = world_from_document(row.document)
    require_cursor(world, row, guard)
    return world


def changed_commands(
    previous: WorldState, current: WorldState
) -> list[AcceptedCommand]:
    before = {command.id: command for command in previous.accepted_commands}
    return [
        command
        for command in current.accepted_commands
        if before.get(command.id) != command
    ]


def removed_command_ids(previous: WorldState, current: WorldState) -> list[str]:
    remaining = {command.id for command in current.accepted_commands}
    return [
        command.id
        for command in previous.accepted_commands
        if command.id not in remaining
    ]
