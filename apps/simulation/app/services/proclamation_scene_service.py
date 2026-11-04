from uuid import UUID, uuid4

from app.engine.proclamations.decision import (
    enact_proclamation_decision,
    require_proclamation_allowed,
)
from app.engine.proclamations.stances import evaluate_minister_stances
from app.engine.world_document import world_from_document
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.models.battle_progress import OperationGuard
from app.models.replay import ProclamationDecisionReplayInput
from app.models.world_state import WorldState
from app.repositories import world_state_repo
from app.services.campaign_transaction import (
    CampaignTransaction,
    CampaignTransition,
    LockedCampaign,
    TransitionFunction,
    require_owner,
)
from psycopg import AsyncConnection
from strategy_contracts.proclamation import (
    ActiveProclamation,
    ProclamationDraft,
    ProclamationScenePackage,
    ProclamationVerdict,
)

ROUTE_DECISION = "proclamation_decision"
COUNCIL_EXCHANGE_CAP = 6


def _decision_transition(
    replay_input: ProclamationDecisionReplayInput,
) -> TransitionFunction:
    async def transition(locked: LockedCampaign) -> CampaignTransition:
        world = locked.world.model_copy(deep=True)
        event = enact_proclamation_decision(world, replay_input)
        return CampaignTransition(world, [event], replay_input=replay_input)

    return transition


class ProclamationSceneService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection
        self._transactions = CampaignTransaction(connection)

    async def convene_council(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        draft: ProclamationDraft,
        is_rescinding_previous: bool = False,
    ) -> ProclamationScenePackage:
        async with self._connection.transaction():
            await require_owner(self._connection, playthrough_id, user_id)
            world = await self._load_world(playthrough_id)
            require_proclamation_allowed(world, is_rescinding_previous)
            return ProclamationScenePackage(
                scene_id=str(uuid4()),
                draft=draft,
                ministers=evaluate_minister_stances(world, draft),
                exchange_cap=COUNCIL_EXCHANGE_CAP,
                is_rescinding_previous=is_rescinding_previous,
            )

    async def decide_proclamation(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        guard: OperationGuard,
        draft: ProclamationDraft,
        verdict: ProclamationVerdict,
        is_rescinding_previous: bool = False,
    ) -> ActiveProclamation:
        replay_input = ProclamationDecisionReplayInput(
            guard=guard,
            draft=draft,
            verdict=verdict,
            is_rescinding_previous=is_rescinding_previous,
        )
        await self._transactions.run(
            playthrough_id,
            user_id,
            guard,
            ROUTE_DECISION,
            replay_input.model_dump(mode="json", exclude={"kind"}),
            _decision_transition(replay_input),
        )
        return await self._enacted_proclamation(playthrough_id)

    async def _enacted_proclamation(self, playthrough_id: UUID) -> ActiveProclamation:
        async with self._connection.transaction():
            world = await self._load_world(playthrough_id)
        if world.active_proclamation is None:
            raise PlaythroughNotFoundError()
        return world.active_proclamation

    async def _load_world(self, playthrough_id: UUID) -> WorldState:
        row = await world_state_repo.get_world_state(self._connection, playthrough_id)
        if row is None:
            raise PlaythroughNotFoundError()
        return world_from_document(row.document)
