import httpx
import structlog
from app.config import Settings
from app.engine.speech_grade import deterministic_fallback_outcome, graded_outcome
from app.integrations.llm_client import SpeechProviderClient
from app.models.speech_grading import SpeechBriefing
from pydantic import ValidationError
from strategy_contracts.scene import BattleSpeechOutcome

logger = structlog.get_logger(__name__)


async def grade_briefing(
    briefing: SpeechBriefing,
    settings: Settings,
    client: SpeechProviderClient | None = None,
) -> BattleSpeechOutcome:
    """Grade all talks together; any provider failure falls back to a 0% swing."""
    if not settings.speech_provider_enabled:
        return deterministic_fallback_outcome()
    provider = client or SpeechProviderClient()
    try:
        answer = await provider.grade_speech(settings, briefing)
    except (httpx.HTTPError, TimeoutError, ValueError, ValidationError) as error:
        logger.warning("speech_grade_fell_back", error_type=type(error).__name__)
        return deterministic_fallback_outcome()
    return graded_outcome(answer.as_scores())
