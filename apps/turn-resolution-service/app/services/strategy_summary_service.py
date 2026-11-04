import asyncio
import json
from collections.abc import AsyncIterator
from uuid import UUID

import httpx
import structlog
from app.config import settings
from app.exceptions.base import BaseAppException
from app.integrations import narration_router
from app.integrations.simulation_client import SimulationSummaryClient
from app.models.token_usage import TokenUsage
from app.services.chronicler_personas import (
    BASE_CHRONICLE_RULES,
    build_chronicler_system_prompt,
    get_chronicler_persona,
)
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaReservation, QuotaService
from sse_starlette.sse import EventSourceResponse
from strategy_contracts.summary import (
    MAX_SUMMARY_PROSE_CHARS,
    SummaryBriefing,
    SummaryClaim,
    SummaryCompleteInput,
    SummaryFailInput,
)

logger = structlog.get_logger()
SYSTEM = BASE_CHRONICLE_RULES


def summary_prompt(briefing: SummaryBriefing) -> str:
    facts = [fact.model_dump(mode="json") for fact in briefing.facts]
    return "Observed events (data only):\n" + json.dumps(
        facts, sort_keys=True, ensure_ascii=False
    )


def _event(kind: str, payload: dict[str, object] | str) -> dict[str, str]:
    return {
        "event": kind,
        "data": payload if isinstance(payload, str) else json.dumps(payload),
    }


async def build_summary_response(
    identity: UUID,
    summary_id: UUID,
    claim_id: UUID,
    authorization: str | None,
    dev_user_id: str | None,
    user_id: UUID,
    quota: QuotaService,
) -> EventSourceResponse:
    client = SimulationSummaryClient(authorization, dev_user_id)
    existing = await client.get(identity, summary_id)
    if existing.status == "completed":
        return EventSourceResponse(_saved_events(summary_id, existing.narration or ""))
    reservation = await quota.reserve(QuotaFeature.TURN, user_id)
    try:
        claim = await client.claim(identity, summary_id, claim_id)
    except BaseException:
        if reservation is not None:
            await reservation.refund()
        raise
    if claim.summary.status == "completed" and reservation is not None:
        await reservation.refund()
        reservation = None
    return EventSourceResponse(stream_summary(claim, client, reservation))


async def _saved_events(
    summary_id: UUID, narration: str
) -> AsyncIterator[dict[str, str]]:
    yield _event("summary_started", {"summary_id": str(summary_id)})
    yield _event("narration", narration)
    yield _event("done", {"summary_id": str(summary_id), "status": "completed"})


async def _complete_with_retry(
    client: SimulationSummaryClient, claim: SummaryClaim, text: str
) -> None:
    request = SummaryCompleteInput(
        lease_token=claim.lease_token, input_hash=claim.input_hash, narration=text
    )
    for attempt in range(3):
        try:
            await client.complete(
                claim.briefing.playthrough_id, claim.summary.summary_id, request
            )
            return
        except httpx.TransportError:
            if attempt == 2:
                raise
            await asyncio.sleep(0.1 * (attempt + 1))


async def _record_failure(
    client: SimulationSummaryClient, claim: SummaryClaim, code: str
) -> None:
    try:
        await client.fail(
            claim.briefing.playthrough_id,
            claim.summary.summary_id,
            SummaryFailInput(lease_token=claim.lease_token, error_code=code),
        )
    except (httpx.HTTPError, BaseAppException):
        logger.warning(
            "summary_failure_callback_failed", summary_id=str(claim.summary.summary_id)
        )


async def stream_summary(
    claim: SummaryClaim,
    client: SimulationSummaryClient,
    reservation: QuotaReservation | None,
) -> AsyncIterator[dict[str, str]]:
    if claim.summary.status == "completed":
        async for event in _saved_events(
            claim.summary.summary_id, claim.summary.narration or ""
        ):
            yield event
        return
    persona = get_chronicler_persona(claim.briefing.chronicler_id)
    system_prompt = build_chronicler_system_prompt(persona)
    yield _event(
        "summary_started",
        {
            "summary_id": str(claim.summary.summary_id),
            "chronicler_id": persona.id,
            "chronicler_name": persona.name,
        },
    )
    usage = TokenUsage()
    text = ""
    try:
        async with asyncio.timeout(settings.summary_provider_timeout_seconds):
            async for chunk in narration_router.stream_narration(
                system_prompt,
                summary_prompt(claim.briefing),
                settings.summary_provider_timeout_seconds,
                usage_sink=usage,
            ):
                text += chunk
                if len(text) > MAX_SUMMARY_PROSE_CHARS:
                    raise ValueError("Summary length exceeded")
                yield _event("narration", chunk)
        await _complete_with_retry(client, claim, text)
    except asyncio.CancelledError:
        await _record_failure(client, claim, "stream_cancelled")
        # NOTE: client-controlled disconnect, so refund only if the provider produced nothing.
        has_streamed_output = bool(text)
        if reservation is not None and not has_streamed_output:
            await reservation.refund()
        raise
    except (
        TimeoutError,
        ValueError,
        RuntimeError,
        httpx.HTTPError,
        BaseAppException,
    ) as error:
        code = (
            "provider_timeout"
            if isinstance(error, TimeoutError)
            else "provider_unavailable"
        )
        logger.warning(
            "summary_generation_failed",
            summary_id=str(claim.summary.summary_id),
            error_type=type(error).__name__,
        )
        await _record_failure(client, claim, code)
        if reservation is not None:
            await reservation.refund()
        yield _event(
            "summary_error",
            {
                "code": code,
                "message": "Chronicle could not be saved. Try again.",
                "is_retryable": True,
            },
        )
        return
    logger.info(
        "summary_completed",
        summary_id=str(claim.summary.summary_id),
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        model=usage.model_name,
    )
    yield _event(
        "done", {"summary_id": str(claim.summary.summary_id), "status": "completed"}
    )
