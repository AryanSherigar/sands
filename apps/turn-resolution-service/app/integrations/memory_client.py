"""Memory service client for Turn Resolution Service.

The only file permitted to call the greenfield memory service (apps/memory).
The base URL and service name are read only from `app.config`. It never logs
request or response payloads, only error types and codes: requests carry the
player's prose and responses carry retrieved story text.
"""

from __future__ import annotations

import uuid

import httpx
import structlog
from app.config import settings
from app.exceptions.memory_exceptions import (
    CODE_INVALID_RESPONSE,
    CODE_UNAVAILABLE,
    CODE_UNKNOWN,
    MemoryIngestError,
    MemoryRetrieveError,
    MemoryRetryError,
)
from app.integrations import memory_auth
from app.models.memory import RetrieveRequest, RetrieveResponse
from app.models.memory_ingest import IngestRequest, IngestResponse
from app.models.memory_retry import MemoryRetryResult

logger = structlog.get_logger()

EVENT_MEMORY_INGEST_ERROR = "memory_ingest_error"
EVENT_MEMORY_RETRIEVE_ERROR = "memory_retrieve_error"
EVENT_MEMORY_RETRY_ERROR = "memory_retry_error"
HEADER_DEV_SERVICE_NAME = "x-dev-service-name"
INGEST_ITEMS_PATH = "/v1/ingest/items"
RETRIEVE_PATH = "/v1/retrieve"

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Build the memory HTTP client lazily and cache it.

    Lazy construction avoids binding to settings at import time, keeping this
    module import-safe in any environment (tests) regardless of configuration.
    """
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


async def ingest_items(request: IngestRequest) -> IngestResponse:
    """Deliver outbox items to the memory service.

    Raises MemoryIngestError carrying only memory's error code and HTTP status,
    never request or response text: the request carries player prose.
    """
    try:
        response = await _get_client().post(
            INGEST_ITEMS_PATH,
            json=request.model_dump(mode="json"),
            timeout=settings.memory_relay_request_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        logger.warning(EVENT_MEMORY_INGEST_ERROR, error_type=type(exc).__name__)
        raise MemoryIngestError(CODE_UNAVAILABLE) from exc
    if not response.is_success:
        code = _error_code_of(response)
        logger.warning(
            EVENT_MEMORY_INGEST_ERROR, status_code=response.status_code, code=code
        )
        raise MemoryIngestError(code, upstream_status=response.status_code)
    try:
        return IngestResponse.model_validate(response.json())
    except ValueError as exc:
        logger.warning(EVENT_MEMORY_INGEST_ERROR, error_type=type(exc).__name__)
        raise MemoryIngestError(
            CODE_INVALID_RESPONSE, upstream_status=response.status_code
        ) from exc


async def retrieve(request: RetrieveRequest) -> RetrieveResponse:
    """Ask memory for the eligible recall for one turn.

    Raises MemoryRetrieveError carrying only memory's error code and HTTP
    status. A 409 with code `not_registered` means the playthrough has not been
    delivered to memory yet.
    """
    try:
        response = await _get_client().post(
            RETRIEVE_PATH,
            json=request.model_dump(mode="json"),
            timeout=settings.memory_retrieve_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        logger.warning(EVENT_MEMORY_RETRIEVE_ERROR, error_type=type(exc).__name__)
        raise MemoryRetrieveError(CODE_UNAVAILABLE) from exc
    if not response.is_success:
        code = _error_code_of(response)
        logger.warning(
            EVENT_MEMORY_RETRIEVE_ERROR, status_code=response.status_code, code=code
        )
        raise MemoryRetrieveError(code, upstream_status=response.status_code)
    try:
        return RetrieveResponse.model_validate(response.json())
    except ValueError as exc:
        logger.warning(EVENT_MEMORY_RETRIEVE_ERROR, error_type=type(exc).__name__)
        raise MemoryRetrieveError(
            CODE_INVALID_RESPONSE, upstream_status=response.status_code
        ) from exc


def _retry_path(playthrough_id: uuid.UUID) -> str:
    return f"/v1/playthroughs/{playthrough_id}/memory/retry"


async def retry_memory(playthrough_id: uuid.UUID) -> MemoryRetryResult:
    """Ask memory to reset failed work for one playthrough and run a bounded pass.

    Raises MemoryRetryError carrying only memory's error code and HTTP status.
    """
    try:
        response = await _get_client().post(
            _retry_path(playthrough_id), timeout=settings.memory_retry_timeout_seconds
        )
    except httpx.HTTPError as exc:
        logger.warning(EVENT_MEMORY_RETRY_ERROR, error_type=type(exc).__name__)
        raise MemoryRetryError(CODE_UNAVAILABLE) from exc
    if not response.is_success:
        code = _error_code_of(response)
        logger.warning(
            EVENT_MEMORY_RETRY_ERROR, status_code=response.status_code, code=code
        )
        raise MemoryRetryError(code, upstream_status=response.status_code)
    try:
        return MemoryRetryResult.model_validate(response.json())
    except ValueError as exc:
        logger.warning(EVENT_MEMORY_RETRY_ERROR, error_type=type(exc).__name__)
        raise MemoryRetryError(
            CODE_INVALID_RESPONSE, upstream_status=response.status_code
        ) from exc
