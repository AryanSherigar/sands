from functools import partial
from uuid import UUID

from app.engine.world_document import world_from_document
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.persistence import SceneExchangeRow, SceneRow
from app.models.world_state import WorldState
from app.repositories import (
    playthrough_repo,
    scene_exchange_repo,
    scene_repo,
    world_state_repo,
)
from app.services.campaign_transaction import (
    CampaignTransaction,
    current_guard,
    require_owner,
)
from app.services.negotiation_closing import attach_refused_demand, close_transition
from app.services.negotiation_service import (
    FINAL_STATUSES,
    exchange_view,
    exchanges_remaining,
    pending_proposal,
)
from app.services.scene_kinds import SceneInterpretation, interpret_scene_decision
from psycopg import AsyncConnection
from strategy_contracts.scene import (
    SceneOutcome,
    ScenePackage,
    SceneStatus,
    SubmissionStatus,
    TermsCardOutcome,
)
from strategy_contracts.scene_exchange import (
    InternalScenePackage,
    SceneExchangeResult,
    SceneExchangeSubmission,
    SceneFailureResult,
)

REASON_SCENE_ENDED = "scene_ended"
REASON_OUT_OF_ORDER = "out_of_order"
REASON_EXCHANGE_CAP = "exchange_cap"
MAX_SCENE_FAILURES = 3


def _result(
    scene: SceneRow,
    exchanges: list[SceneExchangeRow],
    status: SubmissionStatus,
    reason: str | None = None,
) -> SceneExchangeResult:
    return SceneExchangeResult(
        status=status,
        scene_status=scene.status,
        exchanges_remaining=exchanges_remaining(scene, exchanges),
        pending_proposal=pending_proposal(scene, exchanges),
        reason=reason,
    )


def _precheck(
    scene: SceneRow,
    exchanges: list[SceneExchangeRow],
    submission: SceneExchangeSubmission,
) -> SceneExchangeResult | None:
    if submission.sequence <= len(exchanges):
        return _result(scene, exchanges, SubmissionStatus.DUPLICATE_IGNORED)
    rejection = _rejection_reason(scene, exchanges, submission.sequence)
    if rejection is None:
        return None
    return _result(scene, exchanges, SubmissionStatus.REJECTED, rejection)


def _rejection_reason(
    scene: SceneRow, exchanges: list[SceneExchangeRow], sequence: int
) -> str | None:
    if scene.status in FINAL_STATUSES:
        return REASON_SCENE_ENDED
    if sequence != len(exchanges) + 1:
        return REASON_OUT_OF_ORDER
    if exchanges_remaining(scene, exchanges) == 0:
        return REASON_EXCHANGE_CAP
    return None


def _journal_name(outcome: SceneOutcome) -> str:
    if isinstance(outcome, TermsCardOutcome):
        return "resolve_negotiation"
    return "resolve_scene"


def _journal_payload(scene_id: UUID, outcome: SceneOutcome) -> dict[str, object]:
    if isinstance(outcome, TermsCardOutcome):
        return {"scene_id": str(scene_id), "result": outcome.result.value}
    return {"scene_id": str(scene_id), "outcome": outcome.model_dump(mode="json")}


def _failure_result(status: SceneStatus, attempts: int) -> SceneFailureResult:
    return SceneFailureResult(
        scene_status=status,
        failed_attempts=attempts,
        attempts_remaining=max(0, MAX_SCENE_FAILURES - attempts),
    )


def _ending(
    interpretation: SceneInterpretation, remaining_after: int, package: ScenePackage
) -> tuple[SceneOutcome, SceneStatus] | None:
    if interpretation.ending is not None:
        return interpretation.ending, SceneStatus.RESOLVED
    if remaining_after == 0 and interpretation.proposal is None:
        return package.default_outcome, SceneStatus.DEFAULTED
    return None


class SceneExchangeService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection
        self._transaction = CampaignTransaction(connection)

    async def get_package(
        self, scene_id: UUID, acting_user_id: UUID
    ) -> InternalScenePackage:
        """Return the full package, hidden limits included, and mark the scene opened."""
        async with self._connection.transaction():
            scene = await self._owned_scene(scene_id, acting_user_id)
            if await scene_repo.mark_scene_opened(self._connection, scene_id):
                scene = scene.model_copy(update={"status": SceneStatus.OPENED})
            exchanges = await scene_exchange_repo.list_exchanges(
                self._connection, scene_id
            )
            return InternalScenePackage(
                package=scene.package,
                status=scene.status,
                transcript=[exchange_view(row) for row in exchanges],
                exchanges_remaining=exchanges_remaining(scene, exchanges),
            )

    async def submit_exchange(
        self,
        scene_id: UUID,
        acting_user_id: UUID,
        submission: SceneExchangeSubmission,
    ) -> SceneExchangeResult:
        """Append one exchange, bound the model's decision by code, and end the scene if due."""
        async with self._connection.transaction():
            scene = await self._owned_scene(scene_id, acting_user_id)
            exchanges = await scene_exchange_repo.list_exchanges(
                self._connection, scene_id
            )
            early = _precheck(scene, exchanges, submission)
            if early is not None:
                return early
            return await self._record(scene, exchanges, submission, acting_user_id)

    async def report_failure(
        self, scene_id: UUID, acting_user_id: UUID
    ) -> SceneFailureResult:
        """Count a narration failure; enough in a row close the scene with its default outcome."""
        async with self._connection.transaction():
            scene = await self._owned_scene(scene_id, acting_user_id)
            if scene.status in FINAL_STATUSES:
                return _failure_result(scene.status, scene.failed_attempts)
            attempts = await scene_repo.record_failed_attempt(
                self._connection, scene_id
            )
            if attempts is None:
                return _failure_result(scene.status, scene.failed_attempts)
            if attempts < MAX_SCENE_FAILURES:
                return _failure_result(scene.status, attempts)
            await self._close(
                scene,
                acting_user_id,
                scene.package.default_outcome,
                SceneStatus.DEFAULTED,
            )
            return _failure_result(SceneStatus.DEFAULTED, attempts)

    async def _owned_scene(self, scene_id: UUID, acting_user_id: UUID) -> SceneRow:
        scene = await scene_repo.get_scene(self._connection, scene_id)
        if scene is None:
            raise CampaignProgressError("scene unavailable", "not_found", 404)
        await require_owner(self._connection, scene.playthrough_id, acting_user_id)
        return scene

    async def _record(
        self,
        scene: SceneRow,
        exchanges: list[SceneExchangeRow],
        submission: SceneExchangeSubmission,
        acting_user_id: UUID,
    ) -> SceneExchangeResult:
        world = await self._load_world(scene.playthrough_id)
        playthrough = await playthrough_repo.get_playthrough(
            self._connection, scene.playthrough_id
        )
        if playthrough is None:
            raise CampaignProgressError("scene unavailable", "not_found", 404)
        interpretation = interpret_scene_decision(
            submission.decision, scene.package, world, playthrough.scenario
        )
        await scene_exchange_repo.insert_exchange(
            self._connection,
            scene.scene_id,
            submission.sequence,
            submission.player_text,
            submission.leader_text,
            interpretation.proposal,
        )
        await scene_repo.reset_failed_attempts(self._connection, scene.scene_id)
        remaining = exchanges_remaining(scene, exchanges) - 1
        ending = _ending(interpretation, remaining, scene.package)
        if ending is not None:
            ending = attach_refused_demand(
                *ending, pending_proposal(scene, exchanges), submission.tone_grade
            )
            await self._close(scene, acting_user_id, *ending)
        return SceneExchangeResult(
            status=SubmissionStatus.ACCEPTED,
            scene_status=ending[1] if ending else SceneStatus.OPENED,
            exchanges_remaining=remaining,
            pending_proposal=None if ending else interpretation.proposal,
            reason=interpretation.reason,
        )

    async def _load_world(self, playthrough_id: UUID) -> WorldState:
        row = await world_state_repo.get_world_state(self._connection, playthrough_id)
        return world_from_document(row.document)

    async def _close(
        self,
        scene: SceneRow,
        acting_user_id: UUID,
        outcome: SceneOutcome,
        status: SceneStatus,
    ) -> None:
        row = await world_state_repo.get_world_state(
            self._connection, scene.playthrough_id
        )
        operation_id = f"scene-{scene.scene_id}-close"
        guard = current_guard(world_from_document(row.document), row, operation_id)
        transition = partial(
            close_transition,
            self._connection,
            guard,
            scene.scene_id,
            outcome,
            status,
        )
        await self._transaction.run(
            scene.playthrough_id,
            acting_user_id,
            guard,
            _journal_name(outcome),
            _journal_payload(scene.scene_id, outcome),
            transition,
        )
