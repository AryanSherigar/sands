from functools import partial
from uuid import UUID

from app.engine import negotiation
from app.engine.pressure.wars import find_war
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.api_scenes import (
    OpenNegotiationRequest,
    SceneDecisionRequest,
    SceneParticipantView,
    SceneView,
)
from app.models.battle_progress import MutationResponse, OperationGuard
from app.models.persistence import SceneExchangeRow, SceneRow
from app.models.replay import BeginNegotiationReplayInput
from app.models.world_state import WorldState
from app.repositories import scene_exchange_repo, scene_repo
from app.services.campaign_state import player_faction
from app.services.campaign_transaction import (
    CampaignTransaction,
    CampaignTransition,
    LockedCampaign,
    require_owner,
)
from app.services.negotiation_closing import build_outcome, close_transition
from app.services.negotiation_scene import (
    build_negotiation_package,
    build_peace_package,
)
from psycopg import AsyncConnection
from strategy_contracts.scene import SceneStatus, TermsResult
from strategy_contracts.scene_exchange import SceneExchangeView
from strategy_contracts.terms import TermsCard

FINAL_STATUSES = (SceneStatus.RESOLVED, SceneStatus.DEFAULTED)
EXCHANGE_FIELDS = {"sequence", "player_text", "leader_text", "proposal"}


def exchange_view(row: SceneExchangeRow) -> SceneExchangeView:
    return SceneExchangeView.model_validate(row.model_dump(include=EXCHANGE_FIELDS))


def pending_proposal(
    scene: SceneRow, exchanges: list[SceneExchangeRow]
) -> TermsCard | None:
    if scene.status in FINAL_STATUSES or not exchanges:
        return None
    return exchanges[-1].proposal


def exchanges_remaining(scene: SceneRow, exchanges: list[SceneExchangeRow]) -> int:
    return max(0, scene.package.exchange_cap - len(exchanges))


class NegotiationService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection
        self._transaction = CampaignTransaction(connection)

    async def open(
        self, playthrough_id: UUID, user_id: UUID, request: OpenNegotiationRequest
    ) -> MutationResponse:
        """Start a player-proposed negotiation and pause the planning turn on it."""
        guard = OperationGuard.model_validate(
            request.model_dump(exclude={"counterpart_faction_id"})
        )
        transition = partial(
            self._open_transition, guard, request.counterpart_faction_id
        )
        payload = guard.model_dump(mode="json") | {
            "counterpart_faction_id": request.counterpart_faction_id
        }
        return await self._transaction.run(
            playthrough_id, user_id, guard, "begin_negotiation", payload, transition
        )

    async def decide(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        scene_id: UUID,
        request: SceneDecisionRequest,
    ) -> MutationResponse:
        """Confirm the pending terms card, or decline or abandon the negotiation."""
        guard = OperationGuard.model_validate(
            request.model_dump(exclude={"is_confirmed", "proposal_sequence"})
        )
        transition = partial(
            self._decide_transition,
            guard,
            scene_id,
            request.is_confirmed,
            request.proposal_sequence,
        )
        payload = guard.model_dump(mode="json") | {
            "scene_id": str(scene_id),
            "is_confirmed": request.is_confirmed,
            "proposal_sequence": request.proposal_sequence,
        }
        return await self._transaction.run(
            playthrough_id, user_id, guard, "resolve_negotiation", payload, transition
        )

    async def get_view(
        self, playthrough_id: UUID, user_id: UUID, scene_id: UUID
    ) -> SceneView:
        """Return the owner-safe scene, without hidden limits, for reopening after a refresh."""
        async with self._connection.transaction():
            await require_owner(self._connection, playthrough_id, user_id)
            scene = await scene_repo.get_scene(self._connection, scene_id)
            if scene is None or scene.playthrough_id != playthrough_id:
                raise CampaignProgressError("scene unavailable", "not_found", 404)
            exchanges = await scene_exchange_repo.list_exchanges(
                self._connection, scene_id
            )
            return _scene_view(scene, exchanges)

    async def _open_transition(
        self, guard: OperationGuard, counterpart: str, locked: LockedCampaign
    ) -> CampaignTransition:
        world = negotiation.open_negotiation(
            locked.world, counterpart, guard.operation_id
        )
        build = (
            build_peace_package
            if find_war(world, player_faction(world), counterpart)
            else build_negotiation_package
        )
        package = build(
            world,
            locked.playthrough.scenario,
            world.progress.pending_scene_id,
            counterpart,
        )
        await scene_repo.insert_scene(self._connection, package)
        return CampaignTransition(
            world=world,
            replay_input=BeginNegotiationReplayInput(
                guard=guard, counterpart_faction_id=counterpart
            ),
        )

    async def _decide_transition(
        self,
        guard: OperationGuard,
        scene_id: UUID,
        is_confirmed: bool,
        proposal_sequence: int | None,
        locked: LockedCampaign,
    ) -> CampaignTransition:
        exchanges = await scene_exchange_repo.list_exchanges(self._connection, scene_id)
        if is_confirmed:
            proposal = _require_current_proposal(exchanges, proposal_sequence)
            card = proposal.model_copy(update={"is_confirmed_by_player": True})
            outcome = build_outcome(TermsResult.AGREED, card)
            status = SceneStatus.RESOLVED
        else:
            _require_declinable(locked.world)
            has_proposal = bool(exchanges) and exchanges[-1].proposal is not None
            outcome = build_outcome(TermsResult.REFUSED, None)
            status = SceneStatus.RESOLVED if has_proposal else SceneStatus.DEFAULTED
        return await close_transition(
            self._connection, guard, scene_id, outcome, status, locked
        )


def _require_current_proposal(
    exchanges: list[SceneExchangeRow], sequence: int | None
) -> TermsCard:
    latest = exchanges[-1] if exchanges else None
    if latest is None or latest.proposal is None:
        raise CampaignProgressError("no terms to confirm", "no_proposal", 422)
    if latest.sequence != sequence:
        raise CampaignProgressError("the terms changed", "terms_changed")
    return latest.proposal


def _require_declinable(world: WorldState) -> None:
    pending = world.progress.pending_negotiation
    if pending is not None and not pending.is_declinable:
        raise CampaignProgressError("offer cannot be declined", "not_declinable", 422)


def pending_proposal_sequence(
    scene: SceneRow, exchanges: list[SceneExchangeRow]
) -> int | None:
    if pending_proposal(scene, exchanges) is None:
        return None
    return exchanges[-1].sequence


def _scene_view(scene: SceneRow, exchanges: list[SceneExchangeRow]) -> SceneView:
    package = scene.package
    return SceneView(
        scene_id=scene.scene_id,
        scene_type=scene.scene_type,
        status=scene.status,
        turn=scene.turn,
        initiator=package.initiator,
        is_declinable=package.is_declinable,
        situation=package.situation,
        participants=[
            SceneParticipantView(
                participant_id=item.participant_id,
                kind=item.kind,
                name=item.name,
                trait_ids=item.trait_ids,
            )
            for item in package.participants
        ],
        transcript=[exchange_view(row) for row in exchanges],
        exchanges_remaining=exchanges_remaining(scene, exchanges),
        pending_proposal=pending_proposal(scene, exchanges),
        pending_proposal_sequence=pending_proposal_sequence(scene, exchanges),
        outcome=scene.outcome,
    )
