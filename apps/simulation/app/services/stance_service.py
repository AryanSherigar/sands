import httpx
import structlog
from app.config import Settings
from app.integrations.llm_client import StanceProviderClient
from app.models.stance import StanceChoice, StanceRequest, StanceSource
from pydantic import ValidationError

REASON_MODEL_PICK = "model_pick"
REASON_PROVIDER_DISABLED = "provider_disabled"
REASON_PROVIDER_ERROR = "provider_error"
REASON_OFF_MENU = "off_menu"

logger = structlog.get_logger(__name__)


def is_stance_provider_ready(settings: Settings) -> bool:
    return bool(
        settings.stance_provider_enabled
        and settings.stance_provider_url
        and settings.stance_provider_api_key
        and settings.stance_provider_model
    )


async def create_stance_candidate(
    request: StanceRequest,
    settings: Settings,
    client: StanceProviderClient | None = None,
) -> StanceChoice:
    """Ask the provider for a stance; any failure or off-menu answer yields the fallback."""
    if not is_stance_provider_ready(settings):
        return _fallback(request, REASON_PROVIDER_DISABLED)
    provider = client or StanceProviderClient()
    try:
        answer = await provider.pick_stance(settings, request.briefing)
    except (httpx.HTTPError, TimeoutError, ValueError, ValidationError) as error:
        logger.warning(
            "stance_fell_back",
            reason_code=REASON_PROVIDER_ERROR,
            error_type=type(error).__name__,
            request_id=request.request_id,
            input_hash=request.input_hash,
        )
        return _fallback(request, REASON_PROVIDER_ERROR)
    if answer.option_id not in {item.id for item in request.briefing.menu}:
        logger.warning(
            "stance_fell_back",
            reason_code=REASON_OFF_MENU,
            request_id=request.request_id,
            input_hash=request.input_hash,
        )
        return _fallback(request, REASON_OFF_MENU)
    return request.fallback.model_copy(
        update={
            "option_id": answer.option_id,
            "source": StanceSource.MODEL,
            "reason_code": REASON_MODEL_PICK,
        }
    )


def _fallback(request: StanceRequest, reason_code: str) -> StanceChoice:
    return request.fallback.model_copy(update={"reason_code": reason_code})
