"""Memory client for Core API.

The only file permitted to call the memory service (CLAUDE.md). The base URL
is read only from `app.config`. Authored templates go through `build_template`
and deletion through `purge` and `list_scopes`, all authenticated by the dev
service-identity header, or a Google ID token when IAM auth is enabled.
"""

from __future__ import annotations

from uuid import UUID

import httpx
import structlog
from app.config import settings
from app.exceptions.memory_exceptions import (
    MemoryPurgeError,
    MemoryTemplateBuildError,
)
from app.integrations import memory_auth
from app.models.memory_purge import (
    PURGE_MAX_IDS,
    MemoryPurgeResult,
    MemoryScopes,
    PurgeRequest,
)
from app.models.memory_template import (
    TemplateBuildOutcome,
    TemplateBuildRequest,
    TemplateBuildResponse,
)

logger = structlog.get_logger()

EVENT_MEMORY_TEMPLATE_BUILD_ERROR = "memory_template_build_error"
EVENT_MEMORY_PURGE_ERROR = "memory_purge_error"
EVENT_MEMORY_SCOPES_ERROR = "memory_scopes_error"

HEADER_DEV_SERVICE_NAME = "x-dev-service-name"
TEMPLATES_PATH = "/v1/templates"
PURGE_PATH = "/v1/purge"
SCOPES_PATH = "/v1/scopes"
CODE_UNAVAILABLE = "unavailable"
CODE_UNKNOWN = "unknown"
CODE_INVALID_RESPONSE = "invalid_response"

_client: httpx.AsyncClient | None = None

_CREATED_STATUS_CODE = 201


async def close_memory_client() -> None:
    """Close the cached memory HTTP client and reset the singleton.

    Call from the FastAPI lifespan shutdown handler in main.py, alongside
    close_db_connection().
    """
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.memory_url,
            headers={HEADER_DEV_SERVICE_NAME: settings.memory_service_name},
            auth=memory_auth.build_memory_auth(),
        )
    return _client


def _error_code_of(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return CODE_UNKNOWN
    code = body.get("code") if isinstance(body, dict) else None
    return code if isinstance(code, str) and code else CODE_UNKNOWN


async def build_template(request: TemplateBuildRequest) -> TemplateBuildOutcome:
    """Build the memory template for one published revision (idempotent).

    Raises MemoryTemplateBuildError carrying only memory's error code and HTTP
    status, never request or response text: the request carries authored prose
    and the message is persisted to `Scenario.publish_error`.
    """
    try:
        response = await _get_client().post(
            TEMPLATES_PATH,
            json=request.model_dump(mode="json"),
            timeout=settings.memory_template_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        logger.warning(EVENT_MEMORY_TEMPLATE_BUILD_ERROR, error_type=type(exc).__name__)
        raise MemoryTemplateBuildError(CODE_UNAVAILABLE) from exc
    if not response.is_success:
        code = _error_code_of(response)
        logger.warning(
            EVENT_MEMORY_TEMPLATE_BUILD_ERROR,
            status_code=response.status_code,
            code=code,
        )
        raise MemoryTemplateBuildError(code, response.status_code)
    return _to_outcome(response)


def _to_outcome(response: httpx.Response) -> TemplateBuildOutcome:
    try:
        parsed = TemplateBuildResponse.model_validate(response.json())
    except ValueError as exc:
        logger.warning(EVENT_MEMORY_TEMPLATE_BUILD_ERROR, error_type=type(exc).__name__)
        raise MemoryTemplateBuildError(
            CODE_INVALID_RESPONSE, response.status_code
        ) from exc
    return TemplateBuildOutcome(
        response=parsed, was_created=response.status_code == _CREATED_STATUS_CODE
    )


def _chunks(ids: list[UUID]) -> list[list[UUID]]:
    return [
        ids[start : start + PURGE_MAX_IDS]
        for start in range(0, len(ids), PURGE_MAX_IDS)
    ]


async def _send_checked(
    method: str, path: str, event: str, **kwargs: object
) -> httpx.Response:
    try:
        response = await _get_client().request(
            method, path, timeout=settings.memory_purge_timeout_seconds, **kwargs
        )
    except httpx.HTTPError as exc:
        logger.warning(event, error_type=type(exc).__name__)
        raise MemoryPurgeError(CODE_UNAVAILABLE) from exc
    if response.is_success:
        return response
    code = _error_code_of(response)
    logger.warning(event, status_code=response.status_code, code=code)
    raise MemoryPurgeError(code, response.status_code)


async def _purge_chunk(request: PurgeRequest) -> MemoryPurgeResult:
    response = await _send_checked(
        "POST",
        PURGE_PATH,
        EVENT_MEMORY_PURGE_ERROR,
        json=request.model_dump(mode="json"),
    )
    try:
        return MemoryPurgeResult.model_validate(response.json())
    except ValueError as exc:
        logger.warning(EVENT_MEMORY_PURGE_ERROR, error_type=type(exc).__name__)
        raise MemoryPurgeError(CODE_INVALID_RESPONSE, response.status_code) from exc


def _purge_requests(
    playthrough_ids: list[UUID], scenario_ids: list[UUID]
) -> list[PurgeRequest]:
    if len(playthrough_ids) + len(scenario_ids) <= PURGE_MAX_IDS:
        return [
            PurgeRequest(playthrough_ids=playthrough_ids, scenario_ids=scenario_ids)
        ]
    return [
        *(PurgeRequest(playthrough_ids=chunk) for chunk in _chunks(playthrough_ids)),
        *(PurgeRequest(scenario_ids=chunk) for chunk in _chunks(scenario_ids)),
    ]


async def purge(
    playthrough_ids: list[UUID] | None = None,
    scenario_ids: list[UUID] | None = None,
) -> MemoryPurgeResult:
    """Delete memory for playthroughs and scenarios (idempotent, summed over chunks).

    Memory accepts at most PURGE_MAX_IDS ids per call, so larger sets are sent in
    chunks, playthroughs first. Raises MemoryPurgeError carrying only memory's error
    code and HTTP status; the first failing chunk stops the call.
    """
    if not playthrough_ids and not scenario_ids:
        return MemoryPurgeResult()
    requests = _purge_requests(playthrough_ids or [], scenario_ids or [])
    results = [await _purge_chunk(request) for request in requests]
    return MemoryPurgeResult(
        playthroughs_purged=sum(item.playthroughs_purged for item in results),
        templates_purged=sum(item.templates_purged for item in results),
        templates_retained_in_use=sum(
            item.templates_retained_in_use for item in results
        ),
    )


async def list_scopes() -> MemoryScopes:
    """List every playthrough and template scope memory holds, for orphan reconciliation."""
    response = await _send_checked("GET", SCOPES_PATH, EVENT_MEMORY_SCOPES_ERROR)
    try:
        return MemoryScopes.model_validate(response.json())
    except ValueError as exc:
        logger.warning(EVENT_MEMORY_SCOPES_ERROR, error_type=type(exc).__name__)
        raise MemoryPurgeError(CODE_INVALID_RESPONSE, response.status_code) from exc
