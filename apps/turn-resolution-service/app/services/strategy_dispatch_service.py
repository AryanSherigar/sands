import asyncio
import json
from collections.abc import AsyncIterator
from uuid import UUID

import httpx
import structlog
from app.config import settings
from app.exceptions.base import BaseAppException
from app.integrations import openai_compatible_client
from app.integrations.simulation_client import SimulationDispatchClient
from app.models.token_usage import TokenUsage
from app.services.dispatch_prompt import build_dispatch_prompt
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaReservation, QuotaService
from sse_starlette.sse import EventSourceResponse
from strategy_contracts.agents import (
    MAX_DISPATCH_PROSE_CHARS,
    DispatchClaim,
    DispatchCompleteInput,
    DispatchErrorCode,
    DispatchFailInput,
)

logger = structlog.get_logger()
COMPLETE_ATTEMPTS = 3
DEGRADED_MESSAGE = "The dispatch could not be written. Read the short note instead."


def _event(kind: str, payload: dict[str, object] | str) -> dict[str, str]:
    return {
        "event": kind,
        "data": payload if isinstance(payload, str) else json.dumps(payload),
    }


async def build_dispatch_response(
    identity: UUID,
    rumor_id: str,
    claim_id: UUID,
    authorization: str | None,
    dev_user_id: str | None,
    user_id: UUID,
    quota: QuotaService,
) -> EventSourceResponse:
    client = SimulationDispatchClient(authorization, dev_user_id)
    existing = await client.get(identity, rumor_id)
    if existing.status == "completed":
        return EventSourceResponse(_saved_events(rumor_id, existing.narration or ""))
    reservation = await quota.reserve(QuotaFeature.TURN, user_id)
    try:
        claim = await client.claim(identity, rumor_id, claim_id)
    except BaseException:
        if reservation is not None:
            await reservation.refund()
        raise
    if claim.dispatch.status == "completed" and reservation is not None:
        await reservation.refund()
        reservation = None
    return EventSourceResponse(stream_dispatch(claim, client, reservation))


async def _saved_events(rumor_id: str, narration: str) -> AsyncIterator[dict[str, str]]:
    yield _event("dispatch_started", {"rumor_id": rumor_id})
    yield _event("narration", narration)
    yield _event("done", {"rumor_id": rumor_id, "status": "completed"})


async def _complete_with_retry(
    client: SimulationDispatchClient, claim: DispatchClaim, text: str
) -> None:
    assert claim.briefing is not None and claim.lease_token is not None
    request = DispatchCompleteInput(lease_token=claim.lease_token, narration=text)
    for attempt in range(COMPLETE_ATTEMPTS):
        try:
            await client.complete(
                claim.briefing.playthrough_id, claim.dispatch.rumor_id, request
            )
            return
        except httpx.TransportError:
            if attempt == COMPLETE_ATTEMPTS - 1:
                raise
            await asyncio.sleep(0.1 * (attempt + 1))


async def _record_failure(
    client: SimulationDispatchClient, claim: DispatchClaim, code: DispatchErrorCode
) -> None:
    assert claim.briefing is not None and claim.lease_token is not None
    try:
        await client.fail(
            claim.briefing.playthrough_id,
            claim.dispatch.rumor_id,
            DispatchFailInput(lease_token=claim.lease_token, error_code=code),
        )
    except (httpx.HTTPError, BaseAppException):
        logger.warning(
            "dispatch_failure_callback_failed", rumor_id=claim.dispatch.rumor_id
        )


async def _write_dispatch(
    claim: DispatchClaim, usage: TokenUsage
) -> AsyncIterator[str]:
    assert claim.briefing is not None
    prompt = build_dispatch_prompt(claim.briefing)
    async with asyncio.timeout(settings.summary_provider_timeout_seconds):
        async for chunk in openai_compatible_client.stream_narration(
            prompt.system,
            prompt.user,
            settings.summary_provider_timeout_seconds,
            usage_sink=usage,
        ):
            yield chunk


def _error_code(error: Exception) -> DispatchErrorCode:
    if isinstance(error, TimeoutError):
        return "provider_timeout"
    return "provider_unavailable"


async def stream_dispatch(
    claim: DispatchClaim,
    client: SimulationDispatchClient,
    reservation: QuotaReservation | None,
) -> AsyncIterator[dict[str, str]]:
    rumor_id = claim.dispatch.rumor_id
    if claim.dispatch.status == "completed":
        async for event in _saved_events(rumor_id, claim.dispatch.narration or ""):
            yield event
        return
    yield _event("dispatch_started", {"rumor_id": rumor_id})
    usage = TokenUsage()
    text = ""
    try:
        async for chunk in _write_dispatch(claim, usage):
            text += chunk
            if len(text) > MAX_DISPATCH_PROSE_CHARS:
                raise ValueError("Dispatch length exceeded")
            yield _event("narration", chunk)
        await _complete_with_retry(client, claim, text)
    except asyncio.CancelledError:
        await _record_failure(client, claim, "stream_cancelled")
        # NOTE: client-controlled disconnect, so refund only if the provider produced nothing.
        if reservation is not None and not text:
            await reservation.refund()
        raise
    except (
        TimeoutError,
        ValueError,
        RuntimeError,
        httpx.HTTPError,
        BaseAppException,
    ) as error:
        code = _error_code(error)
        logger.warning(
            "dispatch_generation_failed",
            rumor_id=rumor_id,
            error_type=type(error).__name__,
        )
        await _record_failure(client, claim, code)
        if reservation is not None:
            await reservation.refund()
        yield _event(
            "degraded",
            {"code": code, "message": DEGRADED_MESSAGE, "is_retryable": True},
        )
        return
    logger.info(
        "dispatch_completed",
        rumor_id=rumor_id,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        cached_tokens=usage.cached_tokens,
        model=usage.model_name,
    )
    yield _event("done", {"rumor_id": rumor_id, "status": "completed"})
