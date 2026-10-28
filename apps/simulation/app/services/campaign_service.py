from functools import partial
from uuid import UUID

from app.config import get_settings
from app.engine.campaign import advance_campaign, begin_campaign, resume_campaign
from app.engine.negotiation import require_no_open_negotiation
from app.models.api_commands import EconomyChoiceRequest
from app.models.battle_intelligence import BattleIntent
from app.models.battle_progress import (
    InitializeCampaign,
    MutationResponse,
    OperationGuard,
)
from app.models.replay import (
    AdvanceCampaignReplayInput,
    BeginCampaignReplayInput,
    ResumeEconomyReplayInput,
)
from app.models.world_state import WorldState
from app.repositories import intent_request_repo
from app.services.campaign_initialization import initialize_campaign
from app.services.campaign_transaction import (
    CampaignTransaction,
    CampaignTransition,
    LockedCampaign,
    from_turn,
)
from app.services.economy_scene import resolve_economy_choice
from app.services.intent_briefing import schedule_intent_requests
from app.services.stance_transition import freeze_next_stances, settle_stances
from app.services.triggered_negotiation import persist_triggered_scene
from psycopg import AsyncConnection


class CampaignService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection
        self._transaction = CampaignTransaction(connection)

    async def initialize(self, request: InitializeCampaign) -> MutationResponse:
        """Initialize under a transaction-scoped advisory lock after internal service authentication."""
        return await initialize_campaign(self._connection, request)

    async def begin(
        self, playthrough_id: UUID, user_id: UUID, guard: OperationGuard
    ) -> MutationResponse:
        """Commit pre-battle campaign phases or a completed turn with one operation receipt."""

        async def transition(locked: LockedCampaign) -> CampaignTransition:
            require_no_open_negotiation(locked.world)
            scenario = locked.playthrough.scenario
            frozen = await freeze_next_stances(self._connection, locked.world)
            result = from_turn(
                begin_campaign(locked.world, scenario, recorded_stances=frozen)
            )
            await schedule_intent_requests(
                self._connection, result.world, scenario, get_settings()
            )
            stances = await settle_stances(
                self._connection,
                locked.world,
                result.world,
                scenario,
                get_settings(),
                frozen,
            )
            await persist_triggered_scene(self._connection, result.world, scenario)
            result.replay_input = BeginCampaignReplayInput(guard=guard, stances=stances)
            return result

        return await self._transaction.run(
            playthrough_id,
            user_id,
            guard,
            "begin_campaign",
            guard.model_dump(mode="json"),
            transition,
        )

    async def advance(
        self, playthrough_id: UUID, user_id: UUID, guard: OperationGuard
    ) -> MutationResponse:
        """Commit a single synchronized wave and any remaining campaign phases atomically."""

        transition = partial(self._advance_transition, guard)
        return await self._transaction.run(
            playthrough_id,
            user_id,
            guard,
            "advance_campaign",
            guard.model_dump(mode="json"),
            transition,
        )

    async def choose_economy(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        request: EconomyChoiceRequest,
        scene_id: UUID,
    ) -> MutationResponse:
        """Map the HTTP choice model to the canonical transaction request."""
        guard = OperationGuard.model_validate(request.model_dump(exclude={"choice"}))
        return await self.resume_economy(
            playthrough_id, user_id, guard, scene_id, request.choice
        )

    async def resume_economy(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        guard: OperationGuard,
        scene_id: UUID,
        choice: str,
    ) -> MutationResponse:
        """Resolve a code-only economy choice and resume its paused phase exactly once."""

        transition = partial(self._resume_transition, guard, scene_id, choice)
        payload = guard.model_dump(mode="json") | {
            "scene_id": str(scene_id),
            "choice": choice,
        }
        return await self._transaction.run(
            playthrough_id, user_id, guard, "resume_economy", payload, transition
        )

    async def _advance_transition(
        self, guard: OperationGuard, locked: LockedCampaign
    ) -> CampaignTransition:
        intents = await intent_request_repo.freeze_intents(
            self._connection,
            locked.world.playthrough_id,
            guard.expected_turn,
            guard.expected_wave,
        )
        scenario = locked.playthrough.scenario
        frozen = await freeze_next_stances(self._connection, locked.world)
        result = advance_campaign(
            locked.world,
            scenario,
            expected_turn=guard.expected_turn,
            expected_wave=guard.expected_wave,
            recorded_intents=intents,
            recorded_stances=frozen,
        )
        await schedule_intent_requests(
            self._connection, result.result.world, scenario, get_settings()
        )
        stances = await settle_stances(
            self._connection,
            locked.world,
            result.result.world,
            scenario,
            get_settings(),
            frozen,
        )
        await persist_triggered_scene(self._connection, result.result.world, scenario)
        transition = from_turn(result.result, result.receipts)
        transition.replay_input = AdvanceCampaignReplayInput(
            guard=guard,
            intents=_activated_intents(result.result.world, guard),
            stances=stances,
        )
        return transition

    async def _resume_transition(
        self,
        guard: OperationGuard,
        scene_id: UUID,
        choice: str,
        locked: LockedCampaign,
    ) -> CampaignTransition:
        outcome = await resolve_economy_choice(
            self._connection, locked.world, scene_id, choice
        )
        scenario = locked.playthrough.scenario
        frozen = await freeze_next_stances(self._connection, locked.world)
        result = resume_campaign(
            locked.world, scenario, {scene_id: outcome}, recorded_stances=frozen
        )
        stances = await settle_stances(
            self._connection,
            locked.world,
            result.world,
            scenario,
            get_settings(),
            frozen,
        )
        await persist_triggered_scene(self._connection, result.world, scenario)
        transition = from_turn(result)
        transition.replay_input = ResumeEconomyReplayInput(
            guard=guard, scene_id=scene_id, choice=choice, stances=stances
        )
        return transition


def _activated_intents(world: WorldState, guard: OperationGuard) -> list[BattleIntent]:
    return [
        intent
        for _, intent in sorted(world.battle_intents.items())
        if intent.campaign_turn == guard.expected_turn
        and intent.activation_wave == guard.expected_wave
    ]
