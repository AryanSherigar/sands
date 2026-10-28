from uuid import UUID

import httpx
import structlog
from app.config import Settings
from app.engine.speech_grade import deterministic_fallback_outcome, graded_outcome
from app.engine.world_document import world_from_document
from app.exceptions.command_exceptions import CampaignProgressError
from app.integrations.llm_client import SpeechProviderClient
from app.models.speech_grading import SpeechBriefing, SpeechGradeRequest
from app.repositories import world_state_repo
from app.services.campaign_state import player_faction
from app.services.campaign_transaction import require_owner
from app.services.speech_briefing import build_speech_briefing
from psycopg import AsyncConnection
from pydantic import ValidationError
from strategy_contracts.scene import BattleSpeechOutcome

logger = structlog.get_logger(__name__)


async def grade_briefing(
    briefing: SpeechBriefing,
    settings: Settings,
    client: SpeechProviderClient | None = None,
) -> BattleSpeechOutcome:
    if not settings.speech_provider_enabled:
        return deterministic_fallback_outcome()
    provider = client or SpeechProviderClient()
    try:
        answer = await provider.grade_speech(settings, briefing)
    except (httpx.HTTPError, TimeoutError, ValueError, ValidationError) as error:
        logger.warning("speech_grade_fell_back", error_type=type(error).__name__)
        return deterministic_fallback_outcome()
    return graded_outcome(answer.as_scores())


class SpeechGradeService:
    def __init__(
        self,
        connection: AsyncConnection,
        settings: Settings,
        client: SpeechProviderClient | None = None,
    ) -> None:
        self._connection = connection
        self._settings = settings
        self._client = client

    async def grade_speech(
        self, playthrough_id: UUID, acting_user_id: UUID, request: SpeechGradeRequest
    ) -> BattleSpeechOutcome:
        """Grade a speech to the player's army; falls back to a 0% swing on any provider failure."""
        async with self._connection.transaction():
            playthrough = await require_owner(
                self._connection, playthrough_id, acting_user_id
            )
            row = await world_state_repo.get_world_state(
                self._connection, playthrough_id
            )
        world = world_from_document(row.document)
        army = world.armies.get(request.army_id)
        if army is None or army.owner_id != player_faction(world):
            raise CampaignProgressError("army unavailable", "not_found", 404)
        briefing = build_speech_briefing(
            world, playthrough.scenario, request.army_id, request.speech_text
        )
        return await grade_briefing(briefing, self._settings, self._client)
