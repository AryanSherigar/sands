import json
from uuid import UUID, uuid4

import httpx
import structlog
from app.exceptions.base import BaseAppException
from app.integrations.narration_router import chat_completion
from app.integrations.simulation_client import SimulationEventNarrativeClient
from app.services.event_prompt import build_event_prompt
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService
from pydantic import ValidationError
from strategy_contracts.events import (
    EventNarrativeClaim,
    EventNarrativeCompleteInput,
    EventNarrativeFailInput,
    EventNarrativePayload,
)

logger = structlog.get_logger(__name__)
ERROR_CODE_GENERATION_FAILED = "generation_error"
NARRATION_FAILURES = (
    BaseAppException,
    httpx.HTTPError,
    ValueError,
    TypeError,
    ValidationError,
    RuntimeError,
    TimeoutError,
)


async def _claim_delivery(
    client: SimulationEventNarrativeClient, playthrough_id: UUID, event_id: str
) -> EventNarrativeClaim | None:
    try:
        return await client.claim(playthrough_id, event_id, uuid4())
    except BaseAppException as exc:
        if exc.status_code == 409:
            return None
        raise


async def _fail_delivery(
    client: SimulationEventNarrativeClient,
    playthrough_id: UUID,
    event_id: str,
    lease_token: UUID,
) -> None:
    try:
        await client.fail(
            playthrough_id,
            event_id,
            EventNarrativeFailInput(
                lease_token=lease_token, error_code=ERROR_CODE_GENERATION_FAILED
            ),
        )
    except (httpx.HTTPError, BaseAppException) as exc:
        logger.warning("event_fail_callback_failed", event_id=event_id, error=str(exc))


async def _generate_payload(
    prompt_system: str,
    prompt_user: str,
    schema_dict: dict[str, object],
) -> EventNarrativePayload:
    raw = await chat_completion(
        system_prompt=prompt_system,
        user_message=prompt_user,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "narrative", "schema": schema_dict},
        },
    )
    return EventNarrativePayload.model_validate(json.loads(raw))


async def _generate_and_complete(
    claim: EventNarrativeClaim,
    client: SimulationEventNarrativeClient,
    playthrough_id: UUID,
    event_id: str,
) -> EventNarrativePayload | None:
    prompt = build_event_prompt(claim.briefing)
    try:
        payload = await _generate_payload(
            prompt.system, prompt.user, prompt.schema_dict
        )
        await client.complete(
            playthrough_id,
            event_id,
            EventNarrativeCompleteInput(
                lease_token=claim.lease_token, narration=payload
            ),
        )
        return payload
    except NARRATION_FAILURES as exc:
        logger.warning("event_narration_failed", event_id=event_id, error=str(exc))
        await _fail_delivery(client, playthrough_id, event_id, claim.lease_token)
        return None


async def narrate_strategy_event(
    playthrough_id: UUID,
    event_id: str,
    client: SimulationEventNarrativeClient,
    user_id: UUID,
    quota: QuotaService,
) -> EventNarrativePayload | None:
    existing = await client.get(playthrough_id, event_id)
    if existing.status == "completed" and existing.narration is not None:
        return existing.narration

    claim = await _claim_delivery(client, playthrough_id, event_id)
    if claim is None:
        return None

    reservation = await quota.reserve(QuotaFeature.STRATEGY_EVENT, user_id)
    payload = await _generate_and_complete(claim, client, playthrough_id, event_id)
    if payload is None and reservation is not None:
        await reservation.refund()
    return payload
