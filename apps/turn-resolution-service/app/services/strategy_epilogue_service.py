import asyncio
import json
from collections.abc import AsyncIterator
from uuid import UUID

import httpx
import structlog
from app.config import settings
from app.exceptions.base import BaseAppException
from app.integrations import narration_router
from app.integrations.simulation_client import SimulationEpilogueClient
from app.models.token_usage import TokenUsage
from app.services.chronicler_personas import get_chronicler_persona
from app.services.epilogue_prompt import build_epilogue_system_prompt, epilogue_prompt
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaReservation, QuotaService
from sse_starlette.sse import EventSourceResponse
from strategy_contracts.epilogue import (
    MAX_EPILOGUE_PROSE_CHARS,
    EpilogueClaim,
    EpilogueCompleteInput,
    EpilogueFailInput,
)

logger = structlog.get_logger()

SAVE_ATTEMPTS = 3
SAVE_RETRY_DELAY_SECONDS = 0.1
FAILURE_MESSAGE = "The closing entry could not be saved. Try again."
_RECOVERABLE_ERRORS = (
    TimeoutError,
    ValueError,
    RuntimeError,
    httpx.HTTPError,
    BaseAppException,
)


def _event(kind: str, payload: dict[str, object] | str) -> dict[str, str]:
    return {
        "event": kind,
        "data": payload if isinstance(payload, str) else json.dumps(payload),
    }


def _saved_events(narration: str) -> list[dict[str, str]]:
    return [
        _event("epilogue_started", {"status": "completed"}),
        _event("narration", narration),
        _event("done", {"status": "completed"}),
    ]


async def build_epilogue_response(
    identity: UUID,
    claim_id: UUID,
    authorization: str | None,
    dev_user_id: str | None,
    user_id: UUID,
    quota: QuotaService,
) -> EventSourceResponse:
    client = SimulationEpilogueClient(authorization, dev_user_id)
    existing = await client.get(identity)
    if existing.status == "completed":
        return EventSourceResponse(iter(_saved_events(existing.narration or "")))
    reservation = await quota.reserve(QuotaFeature.TURN, user_id)
    try:
        claim = await client.claim(identity, claim_id)
    except BaseException:
        if reservation is not None:
            await reservation.refund()
        raise
    if claim.epilogue.status == "completed" and reservation is not None:
        await reservation.refund()
        reservation = None
    return EventSourceResponse(stream_epilogue(claim, client, reservation))


async def _save_with_retry(
    client: SimulationEpilogueClient, claim: EpilogueClaim, text: str
) -> None:
    if claim.lease_token is None:
        raise ValueError("an epilogue claim without a lease cannot be saved")
    request = EpilogueCompleteInput(
        lease_token=claim.lease_token, input_hash=claim.input_hash, narration=text
    )
    for attempt in range(SAVE_ATTEMPTS):
        try:
            await client.complete(claim.briefing.playthrough_id, request)
            return
        except httpx.TransportError:
            if attempt == SAVE_ATTEMPTS - 1:
                raise
            await asyncio.sleep(SAVE_RETRY_DELAY_SECONDS * (attempt + 1))


async def _record_failure(
    client: SimulationEpilogueClient, claim: EpilogueClaim, code: str
) -> None:
    if claim.lease_token is None:
        return
    try:
        await client.fail(
            claim.briefing.playthrough_id,
            EpilogueFailInput(lease_token=claim.lease_token, error_code=code),
        )
    except (httpx.HTTPError, BaseAppException):
        logger.warning(
            "epilogue_failure_callback_failed",
            playthrough_id=str(claim.briefing.playthrough_id),
        )


async def _generate(
    claim: EpilogueClaim, chunks: list[str], usage: TokenUsage
) -> AsyncIterator[str]:
    persona = get_chronicler_persona(claim.briefing.chronicler_id)
    async with asyncio.timeout(settings.summary_provider_timeout_seconds):
        async for chunk in narration_router.stream_narration(
            build_epilogue_system_prompt(persona),
            epilogue_prompt(claim.briefing),
            settings.summary_provider_timeout_seconds,
            usage_sink=usage,
        ):
            chunks.append(chunk)
            if len("".join(chunks)) > MAX_EPILOGUE_PROSE_CHARS:
                raise ValueError("Epilogue length exceeded")
            yield chunk


def _failure_code(error: BaseException) -> str:
    if isinstance(error, TimeoutError):
        return "provider_timeout"
    return "provider_unavailable"


async def _handle_cancel(
    client: SimulationEpilogueClient,
    claim: EpilogueClaim,
    reservation: QuotaReservation | None,
    has_output: bool,
) -> None:
    await _record_failure(client, claim, "stream_cancelled")
    if reservation is not None and not has_output:
        await reservation.refund()


def _started_event(claim: EpilogueClaim) -> dict[str, str]:
    persona = get_chronicler_persona(claim.briefing.chronicler_id)
    return _event(
        "epilogue_started",
        {"chronicler_id": persona.id, "chronicler_name": persona.name},
    )


async def _failure_event(
    error: BaseException,
    client: SimulationEpilogueClient,
    claim: EpilogueClaim,
    reservation: QuotaReservation | None,
) -> dict[str, str]:
    logger.warning(
        "epilogue_generation_failed",
        playthrough_id=str(claim.briefing.playthrough_id),
        error_type=type(error).__name__,
    )
    code = _failure_code(error)
    await _record_failure(client, claim, code)
    if reservation is not None:
        await reservation.refund()
    return _event(
        "epilogue_error",
        {"code": code, "message": FAILURE_MESSAGE, "is_retryable": True},
    )


def _log_completion(claim: EpilogueClaim, usage: TokenUsage) -> None:
    logger.info(
        "epilogue_completed",
        playthrough_id=str(claim.briefing.playthrough_id),
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        model=usage.model_name,
    )


async def stream_epilogue(
    claim: EpilogueClaim,
    client: SimulationEpilogueClient,
    reservation: QuotaReservation | None,
) -> AsyncIterator[dict[str, str]]:
    if claim.epilogue.status == "completed":
        for event in _saved_events(claim.epilogue.narration or ""):
            yield event
        return
    yield _started_event(claim)
    chunks: list[str] = []
    usage = TokenUsage()
    try:
        async for chunk in _generate(claim, chunks, usage):
            yield _event("narration", chunk)
        await _save_with_retry(client, claim, "".join(chunks))
    except asyncio.CancelledError:
        await _handle_cancel(client, claim, reservation, bool(chunks))
        raise
    except _RECOVERABLE_ERRORS as error:
        yield await _failure_event(error, client, claim, reservation)
        return
    _log_completion(claim, usage)
    yield _event("done", {"status": "completed"})
