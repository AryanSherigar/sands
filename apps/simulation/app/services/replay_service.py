from uuid import UUID

from app.engine.replay import replay_history
from app.engine.world_document import world_from_document
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.exceptions.world_exceptions import HistoricalReplayUnavailableError
from app.models.api_replay import HistoricalWorldResponse, ReplayVerificationResponse
from app.models.api_world_view import WorldView
from app.models.persistence import SnapshotRow
from app.models.replay import ReplayStep
from app.repositories import replay_step_repo, turn_hash_repo, world_snapshot_repo
from app.services.campaign_transaction import require_owner
from app.services.world_projection import project_world
from psycopg import AsyncConnection

MAX_HISTORY_TURN = 2**31 - 1


class ReplayService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def load_history(
        self, playthrough_id: UUID, user_id: UUID, turn: int
    ) -> HistoricalWorldResponse:
        async with self._connection.transaction():
            playthrough = await require_owner(self._connection, playthrough_id, user_id)
            snapshot = await world_snapshot_repo.get_snapshot(
                self._connection, playthrough_id, turn
            )
            if snapshot is None:
                raise PlaythroughNotFoundError()
            world = world_from_document(snapshot.document)
            projected = project_world(
                world, playthrough.scenario, 1, snapshot.world_hash
            )
            world_view = {
                key: value
                for key, value in projected.model_dump().items()
                if key in WorldView.model_fields
            }
            return HistoricalWorldResponse(
                turn=turn,
                world_hash=snapshot.world_hash,
                world=WorldView.model_validate(world_view),
            )

    async def verify(
        self, playthrough_id: UUID, user_id: UUID, through_turn: int | None
    ) -> ReplayVerificationResponse:
        async with self._connection.transaction():
            playthrough = await require_owner(self._connection, playthrough_id, user_id)
            target = await self._target_snapshot(playthrough_id, through_turn)
            initial = await world_snapshot_repo.get_snapshot(
                self._connection, playthrough_id, 0
            )
            steps = await replay_step_repo.list_steps(self._connection, playthrough_id)
            if initial is None or not steps:
                raise HistoricalReplayUnavailableError()
            result = replay_history(
                world_from_document(initial.document),
                playthrough.scenario,
                _steps_through_snapshot(steps, target.world_hash),
            )
            if result.world_hash != target.world_hash:
                from app.exceptions.world_exceptions import ReplayMismatchError

                raise ReplayMismatchError(
                    result.step_count, target.world_hash, result.world_hash
                )
            await self._require_turn_hash(
                playthrough_id, target.turn, target.world_hash
            )
            return ReplayVerificationResponse(
                verified_turn=target.turn,
                world_hash=result.world_hash,
                step_count=result.step_count,
            )

    async def _target_snapshot(
        self, playthrough_id: UUID, turn: int | None
    ) -> SnapshotRow:
        target_turn = MAX_HISTORY_TURN if turn is None else turn
        snapshot = await world_snapshot_repo.get_latest_snapshot_at_or_before(
            self._connection, playthrough_id, target_turn
        )
        if snapshot is None or (turn is not None and snapshot.turn != turn):
            raise PlaythroughNotFoundError()
        return snapshot

    async def _require_turn_hash(
        self, playthrough_id: UUID, turn: int, snapshot_hash: str
    ) -> None:
        hashes = await turn_hash_repo.list_turn_hashes(self._connection, playthrough_id)
        if turn and not any(
            row.turn == turn and row.world_hash == snapshot_hash for row in hashes
        ):
            from app.exceptions.world_exceptions import ReplayMismatchError

            raise ReplayMismatchError(
                turn, snapshot_hash, "missing-or-mismatched-turn-hash"
            )


def _steps_through_snapshot(
    steps: list[ReplayStep], snapshot_hash: str
) -> list[ReplayStep]:
    for index, step in enumerate(steps, start=1):
        if step.after_hash == snapshot_hash:
            return steps[:index]
    from app.exceptions.world_exceptions import ReplayMismatchError

    raise ReplayMismatchError(0, snapshot_hash, "journal-does-not-reach-snapshot")
