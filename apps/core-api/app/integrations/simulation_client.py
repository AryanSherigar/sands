"""Simulation client for Core API.

The only file permitted to call the simulation service (CLAUDE.md). The base
URL and internal token are read only from `app.config`.
"""

from __future__ import annotations

import httpx
import structlog
from app.config import settings
from app.exceptions.simulation_exceptions import (
    SimulationRejectedError,
    SimulationUnavailableError,
)
from app.models.simulation import InitializeCampaignRequest

logger = structlog.get_logger()

EVENT_SIMULATION_INITIALIZE_ERROR = "simulation_initialize_error"

HEADER_INTERNAL_SERVICE_TOKEN = "X-Internal-Service-Token"
INITIALIZE_PATH = "/internal/v1/playthroughs"
CODE_UNKNOWN = "unknown"
HTTP_SERVER_ERROR_FLOOR = 500

_client: httpx.AsyncClient | None = None


async def close_simulation_client() -> None:
    """Close the cached HTTP client; call from the lifespan shutdown handler."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.simulation_url,
            headers={HEADER_INTERNAL_SERVICE_TOKEN: settings.simulation_internal_token},
        )
    return _client


def _error_code_of(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return CODE_UNKNOWN
    code = body.get("code") if isinstance(body, dict) else None
    return code if isinstance(code, str) and code else CODE_UNKNOWN


async def initialize_campaign(request: InitializeCampaignRequest) -> None:
    """Create the live world for a playthrough (idempotent per operation_id).

    Logs only error codes and statuses, never the request: it carries the
    authored scenario.
    """
    try:
        response = await _get_client().post(
            INITIALIZE_PATH,
            json=request.model_dump(mode="json"),
            timeout=settings.simulation_initialize_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        logger.warning(EVENT_SIMULATION_INITIALIZE_ERROR, error_type=type(exc).__name__)
        raise SimulationUnavailableError() from exc
    if response.is_success:
        return
    code = _error_code_of(response)
    logger.warning(
        EVENT_SIMULATION_INITIALIZE_ERROR, status_code=response.status_code, code=code
    )
    if response.status_code >= HTTP_SERVER_ERROR_FLOOR:
        raise SimulationUnavailableError(response.status_code)
    raise SimulationRejectedError(code, response.status_code)
