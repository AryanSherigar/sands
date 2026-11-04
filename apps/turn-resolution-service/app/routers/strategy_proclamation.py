from typing import Annotated

from app.config import settings
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from app.services.rate_limit.stream_lease_service import (
    StreamLeaseService,
    get_stream_lease_service,
    stream_subject_for_user,
)
from app.services.strategy_proclamation_classifier import (
    classify_sovereign_proclamation,
)
from app.services.strategy_proclamation_dialogue import (
    open_proclamation_dialogue,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from strategy_contracts.proclamation import ProclamationDraft

router = APIRouter(
    prefix="/v1/strategy/proclamation",
    tags=["strategy-proclamation"],
)


class ProclamationClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


class ProclamationNarrateRequest(BaseModel):
    draft: ProclamationDraft
    turn_context: dict[str, object] = Field(default_factory=dict)
    player_speech: str | None = None


@router.post("/classify", response_model=ProclamationDraft)
async def classify_proclamation_endpoint(
    request: ProclamationClassifyRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
) -> ProclamationDraft:
    """Classify the sovereign's freeform proclamation text into a structured draft."""
    return await classify_sovereign_proclamation(request.text, user.user_id, quota)


@router.post("/narrate", response_model=None)
async def narrate_proclamation_endpoint(
    request: ProclamationNarrateRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
    leases: Annotated[StreamLeaseService, Depends(get_stream_lease_service)],
) -> EventSourceResponse:
    """Stream council minister dialogue in response to a proclamation draft."""

    async def build_response() -> EventSourceResponse:
        events = await open_proclamation_dialogue(
            request.draft,
            request.turn_context,
            request.player_speech,
            user.user_id,
            quota,
        )
        return EventSourceResponse(events, ping=settings.sse_ping_interval_seconds)

    return await leases.guard(stream_subject_for_user(user.user_id), build_response)
