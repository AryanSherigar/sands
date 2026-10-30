"""Simulation service client for Turn Resolution Service.

The only file permitted to call the simulation service (apps/simulation). The
base URL and service token are read only from `app.config`. It never logs
request or response bodies, only status codes: exchanges carry the player's
words and packages carry hidden limits.
"""

from __future__ import annotations

import uuid
from typing import TypeVar
from uuid import UUID

import httpx
import structlog
from app.config import settings
from app.exceptions.base import BaseAppException
from app.exceptions.scene_exceptions import (
    HTTP_CONFLICT,
    HTTP_NOT_FOUND,
    SceneNotFoundError,
    SceneNotOpenError,
    SimulationUnavailableError,
)
from app.integrations import memory_auth
from pydantic import BaseModel, ValidationError
from strategy_contracts.base import StrictModel
from strategy_contracts.scene_exchange import (
    InternalScenePackage,
    SceneExchangeResult,
    SceneExchangeSubmission,
    SceneFailureResult,
)
from strategy_contracts.summary import (
    SummaryClaim,
    SummaryClaimInput,
    SummaryCompleteInput,
    SummaryFailInput,
    SummaryView,
)

logger = structlog.get_logger()

EVENT_SIMULATION_REQUEST_ERROR = "simulation_request_error"
HEADER_INTERNAL_SERVICE_TOKEN = "X-Internal-Service-Token"
HEADER_ACTING_USER_ID = "X-Acting-User-Id"
SCENES_PATH = "/internal/v1/scenes"

Model = TypeVar("Model", bound=BaseModel)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Build the simulation HTTP client lazily so import never reads settings."""
    global _client
    if _client is None:
        auth = (
            memory_auth.IdTokenAuth(settings.simulation_url)
            if settings.is_simulation_iam_auth_enabled
            else None
        )
        _client = httpx.AsyncClient(
            base_url=settings.simulation_url,
            timeout=settings.simulation_request_timeout_seconds,
            auth=auth,
        )
    return _client


def _headers(user_id: uuid.UUID) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        HEADER_INTERNAL_SERVICE_TOKEN: settings.internal_service_token,
        HEADER_ACTING_USER_ID: str(user_id),
    }


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == HTTP_NOT_FOUND:
        raise SceneNotFoundError()
    if response.status_code == HTTP_CONFLICT:
        raise SceneNotOpenError()
    if response.is_error:
        logger.warning(EVENT_SIMULATION_REQUEST_ERROR, status=response.status_code)
        raise SimulationUnavailableError(response.status_code)


def _parse(model: type[Model], response: httpx.Response) -> Model:
    try:
        return model.model_validate_json(response.content)
    except ValidationError as error:
        logger.warning(EVENT_SIMULATION_REQUEST_ERROR, error_type="InvalidResponse")
        raise SimulationUnavailableError(response.status_code) from error


async def _send(
    method: str, path: str, user_id: uuid.UUID, body: BaseModel | None = None
) -> httpx.Response:
    try:
        response = await _get_client().request(
            method,
            path,
            headers=_headers(user_id),
            content=None if body is None else body.model_dump_json(),
        )
    except httpx.HTTPError as error:
        logger.warning(EVENT_SIMULATION_REQUEST_ERROR, error_type=type(error).__name__)
        raise SimulationUnavailableError() from error
    _raise_for_status(response)
    return response


async def fetch_scene_package(
    scene_id: uuid.UUID, user_id: uuid.UUID
) -> InternalScenePackage:
    """Fetch the full scene package, hidden limits included, for the narrator."""
    response = await _send("GET", f"{SCENES_PATH}/{scene_id}/package", user_id)
    return _parse(InternalScenePackage, response)


async def submit_exchange(
    scene_id: uuid.UUID, user_id: uuid.UUID, submission: SceneExchangeSubmission
) -> SceneExchangeResult:
    """Record one narrated exchange; the simulation bounds the decision."""
    response = await _send(
        "POST", f"{SCENES_PATH}/{scene_id}/exchanges", user_id, submission
    )
    return _parse(SceneExchangeResult, response)


async def report_scene_failure(
    scene_id: uuid.UUID, user_id: uuid.UUID
) -> SceneFailureResult:
    """Tell the simulation a narration failed; enough in a row end the scene by default."""
    response = await _send("POST", f"{SCENES_PATH}/{scene_id}/failures", user_id)
    return _parse(SceneFailureResult, response)


class SimulationSummaryClient:
    def __init__(self, authorization: str | None, dev_user_id: str | None) -> None:
        self.authorization = authorization
        self.dev_user_id = dev_user_id

    async def _request(
        self, method: str, path: str, body: StrictModel | None = None
    ) -> dict[str, object]:
        headers = {"X-Internal-Service-Token": settings.internal_service_token}
        if self.authorization:
            headers["Authorization"] = self.authorization
        if self.dev_user_id:
            headers["X-Dev-User-Id"] = self.dev_user_id
        async with httpx.AsyncClient(
            timeout=settings.summary_callback_timeout_seconds
        ) as client:
            response = await client.request(
                method,
                settings.simulation_base_url.rstrip("/") + path,
                headers=headers,
                json=body.model_dump(mode="json") if body else None,
            )
        if response.is_error:
            raise BaseAppException(
                "Summary service request failed",
                response.status_code,
                "summary_unavailable",
            )
        return response.json()

    async def get(self, identity: UUID, summary_id: UUID) -> SummaryView:
        return SummaryView.model_validate(
            await self._request(
                "GET", f"/v1/playthroughs/{identity}/summaries/{summary_id}"
            )
        )

    async def claim(
        self, identity: UUID, summary_id: UUID, claim_id: UUID
    ) -> SummaryClaim:
        payload = await self._request(
            "POST",
            f"/internal/v1/playthroughs/{identity}/summaries/{summary_id}/claim",
            SummaryClaimInput(claim_id=claim_id),
        )
        return SummaryClaim.model_validate(payload)

    async def complete(
        self, identity: UUID, summary_id: UUID, request: SummaryCompleteInput
    ) -> SummaryView:
        payload = await self._request(
            "POST",
            f"/internal/v1/playthroughs/{identity}/summaries/{summary_id}/complete",
            request,
        )
        return SummaryView.model_validate(payload)

    async def fail(
        self, identity: UUID, summary_id: UUID, request: SummaryFailInput
    ) -> SummaryView:
        payload = await self._request(
            "POST",
            f"/internal/v1/playthroughs/{identity}/summaries/{summary_id}/fail",
            request,
        )
        return SummaryView.model_validate(payload)
