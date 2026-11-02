from dataclasses import dataclass
from uuid import UUID

import httpx
import structlog
from app.config import Settings
from app.engine.army_mood import NEUTRAL_REACTION
from app.engine.battles.speech import apply_speech_step
from app.engine.world_document import world_from_document
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.exceptions.command_exceptions import CampaignProgressError
from app.integrations.llm_client import SpeechProviderClient
from app.models.api_battle_speech import (
    SpeechTalkRequest,
    SpeechTalkResult,
    SpeechView,
)
from app.models.battle_progress import MutationResponse, OperationGuard
from app.models.replay import SkipBattleSpeechReplayInput, SubmitSpeechTalkReplayInput
from app.models.world_battle import BattleSpeechStatus
from app.models.world_state import WorldState
from app.repositories import operation_repo, world_state_repo
from app.services.battle_speech_view import (
    build_speech_view,
    find_battle_with_speech,
    speech_army_id,
)
from app.services.campaign_transaction import (
    CampaignTransaction,
    CampaignTransition,
    LockedCampaign,
    TransitionFunction,
    require_owner,
)
from app.services.speech_briefing import build_mood_briefing, build_speech_briefing
from app.services.speech_grade_service import grade_briefing
from psycopg import AsyncConnection
from pydantic import ValidationError
from strategy_contracts.battle_speech import MAX_SPEECH_TALKS, CrowdReaction
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import BattleSpeechOutcome

logger = structlog.get_logger(__name__)

ROUTE_TALK = "battle_speech_talk"
ROUTE_SKIP = "battle_speech_skip"
PROVIDER_FAILURES = (httpx.HTTPError, TimeoutError, ValueError, ValidationError)


@dataclass(frozen=True)
class TalkAnswer:
    reaction: CrowdReaction | None = None
    outcome: BattleSpeechOutcome | None = None


def _talk_transition(
    battle_id: str, request: SpeechTalkRequest, answer: TalkAnswer | None
) -> TransitionFunction:
    async def transition(locked: LockedCampaign) -> CampaignTransition:
        if answer is None:
            raise CampaignProgressError("operation unavailable", "invalid_lifecycle")
        replay_input = SubmitSpeechTalkReplayInput(
            guard=request.guard,
            battle_id=battle_id,
            text=request.text,
            reaction=answer.reaction,
            outcome=answer.outcome,
        )
        world = apply_speech_step(locked.world.model_copy(deep=True), replay_input)
        return CampaignTransition(world, replay_input=replay_input)

    return transition


def _skip_transition(battle_id: str, guard: OperationGuard) -> TransitionFunction:
    async def transition(locked: LockedCampaign) -> CampaignTransition:
        replay_input = SkipBattleSpeechReplayInput(guard=guard, battle_id=battle_id)
        world = apply_speech_step(locked.world.model_copy(deep=True), replay_input)
        return CampaignTransition(world, replay_input=replay_input)

    return transition


class BattleSpeechService:
    def __init__(
        self,
        connection: AsyncConnection,
        settings: Settings,
        client: SpeechProviderClient | None = None,
    ) -> None:
        self._connection = connection
        self._settings = settings
        self._client = client or SpeechProviderClient()
        self._transactions = CampaignTransaction(connection)

    async def get_view(
        self, playthrough_id: UUID, user_id: UUID, battle_id: str
    ) -> SpeechView:
        """Read the officer's report, the army's mood and the speech so far."""
        _, world = await self._load(playthrough_id, user_id)
        return build_speech_view(world, battle_id)

    async def submit_talk(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        battle_id: str,
        request: SpeechTalkRequest,
    ) -> SpeechTalkResult:
        """Record the next talk; talks 1 and 2 get a mood, talk 3 grades all three."""
        scenario, world = await self._load(playthrough_id, user_id)
        answer = None
        if not await self._is_known_operation(playthrough_id, user_id, request.guard):
            answer = await self._answer(scenario, world, battle_id, request)
        state = await self._transactions.run(
            playthrough_id,
            user_id,
            request.guard,
            ROUTE_TALK,
            {"battle_id": battle_id, "index": request.talk_index, "text": request.text},
            _talk_transition(battle_id, request, answer),
        )
        return await self._result(playthrough_id, user_id, battle_id, state)

    async def skip(
        self, playthrough_id: UUID, user_id: UUID, battle_id: str, guard: OperationGuard
    ) -> SpeechTalkResult:
        """Leave the speech unsaid: a zero morale swing and no model call."""
        state = await self._transactions.run(
            playthrough_id,
            user_id,
            guard,
            ROUTE_SKIP,
            {"battle_id": battle_id},
            _skip_transition(battle_id, guard),
        )
        return await self._result(playthrough_id, user_id, battle_id, state)

    async def _load(
        self, playthrough_id: UUID, user_id: UUID
    ) -> tuple[StrategyScenario, WorldState]:
        async with self._connection.transaction():
            playthrough = await require_owner(self._connection, playthrough_id, user_id)
            row = await world_state_repo.get_world_state(
                self._connection, playthrough_id
            )
        if row is None:
            raise PlaythroughNotFoundError()
        return playthrough.scenario, world_from_document(row.document)

    async def _is_known_operation(
        self, playthrough_id: UUID, user_id: UUID, guard: OperationGuard
    ) -> bool:
        row = await operation_repo.get_operation(
            self._connection, playthrough_id, str(user_id), guard.operation_id
        )
        return row is not None

    async def _answer(
        self,
        scenario: StrategyScenario,
        world: WorldState,
        battle_id: str,
        request: SpeechTalkRequest,
    ) -> TalkAnswer:
        battle = find_battle_with_speech(world, battle_id)
        speech = battle.speech
        is_next_talk = request.talk_index == len(speech.transcripts) + 1
        if not is_next_talk or speech.status != BattleSpeechStatus.PENDING:
            raise CampaignProgressError("talk out of order", "invalid_lifecycle")
        army_id = speech_army_id(world, battle)
        talks = [*speech.transcripts, request.text]
        if request.talk_index < MAX_SPEECH_TALKS:
            return TalkAnswer(
                reaction=await self._reaction(scenario, world, army_id, talks)
            )
        briefing = build_speech_briefing(world, scenario, army_id, talks)
        outcome = await grade_briefing(briefing, self._settings, self._client)
        return TalkAnswer(outcome=outcome)

    async def _reaction(
        self,
        scenario: StrategyScenario,
        world: WorldState,
        army_id: str,
        talks: list[str],
    ) -> CrowdReaction:
        if not self._settings.speech_provider_enabled:
            return NEUTRAL_REACTION
        briefing = build_mood_briefing(world, scenario, army_id, talks)
        try:
            return await self._client.react_to_talk(self._settings, briefing)
        except PROVIDER_FAILURES as error:
            logger.warning("speech_mood_fell_back", error_type=type(error).__name__)
            return NEUTRAL_REACTION

    async def _result(
        self,
        playthrough_id: UUID,
        user_id: UUID,
        battle_id: str,
        state: MutationResponse,
    ) -> SpeechTalkResult:
        _, world = await self._load(playthrough_id, user_id)
        view = build_speech_view(world, battle_id)
        delta = view.outcome.morale_delta_percent if view.outcome else None
        return SpeechTalkResult(
            reaction=view.reactions[-1] if view.reactions else NEUTRAL_REACTION,
            is_complete=view.outcome is not None,
            morale_delta_percent=delta,
            state=state,
        )
