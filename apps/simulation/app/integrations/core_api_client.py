"""HTTP client for synchronizing turn progression to Core API."""

from uuid import UUID

import httpx
import structlog
from app.config import get_settings

logger = structlog.get_logger()

EVENT_CORE_API_SYNC_ERROR = "core_api_turn_sync_error"
HEADER_INTERNAL_SERVICE_TOKEN = "X-Internal-Service-Token"
TURN_SYNC_PATH_TEMPLATE = "/internal/v1/playthroughs/{playthrough_id}/turn"

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = httpx.AsyncClient(
            base_url=settings.core_api_url,
            headers={HEADER_INTERNAL_SERVICE_TOKEN: settings.internal_service_token},
        )
    return _client


async def close_core_api_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _build_payload(
    turn_count: int,
    is_ended: bool,
    outcome_tag: str | None,
    outcome_title: str | None,
) -> dict[str, object]:
    payload: dict[str, object] = {"turn_count": turn_count, "is_ended": is_ended}
    if is_ended and outcome_tag is not None:
        payload["ended_outcome_tag"] = outcome_tag
    if is_ended and outcome_title is not None:
        payload["ended_outcome_title"] = outcome_title
    return payload


async def sync_turn_count(
    playthrough_id: UUID,
    turn_count: int,
    is_ended: bool = False,
    outcome_tag: str | None = None,
    outcome_title: str | None = None,
) -> None:
    """Best-effort monotonic turn sync to Core API. Logs failures without raising."""
    settings = get_settings()
    url = TURN_SYNC_PATH_TEMPLATE.format(playthrough_id=playthrough_id)
    payload = _build_payload(turn_count, is_ended, outcome_tag, outcome_title)
    try:
        response = await _get_client().patch(
            url, json=payload, timeout=settings.core_api_timeout_seconds
        )
        if not response.is_success:
            logger.warning(
                EVENT_CORE_API_SYNC_ERROR,
                playthrough_id=str(playthrough_id),
                turn_count=turn_count,
                status_code=response.status_code,
            )
    except httpx.HTTPError as exc:
        logger.warning(
            EVENT_CORE_API_SYNC_ERROR,
            playthrough_id=str(playthrough_id),
            turn_count=turn_count,
            error_type=type(exc).__name__,
        )
