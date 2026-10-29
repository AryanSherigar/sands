"""FastAPI router for the live turn-resolution endpoint."""

from typing import Annotated

from app.db.connection import SessionFactory, get_db_session, get_db_session_factory
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.check_event import RuleCheckArmedPayload, RuleCheckArmInput
from app.models.turn import TurnRequestInput
from app.routers.alpha_guards import forbid_when_turns_suspended
from app.services import rule_check_arm_service
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from app.services.rate_limit.stream_lease_service import (
    StreamLeaseService,
    get_stream_lease_service,
    stream_subject_for_user,
)
from app.turn.pipeline import run_turn
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

router = APIRouter(
    prefix="/v1/turn",
    tags=["Turn"],
    dependencies=[Depends(forbid_when_turns_suspended)],
)


@router.post("", response_model=None)
async def submit_turn(
    turn_input: TurnRequestInput,
    session_factory: Annotated[SessionFactory, Depends(get_db_session_factory)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    quota_service: Annotated[QuotaService, Depends(get_quota_service)],
    stream_leases: Annotated[StreamLeaseService, Depends(get_stream_lease_service)],
) -> EventSourceResponse:
    """Submit a player action and stream back narration over SSE."""
    return await stream_leases.guard(
        stream_subject_for_user(current_user.user_id),
        lambda: run_turn(turn_input, session_factory, current_user, quota_service),
    )


@router.post("/rule-check/arm")
async def arm_rule_check(
    arm_input: RuleCheckArmInput,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> RuleCheckArmedPayload:
    """Start the clock of the pending rule check once its narration was read."""
    return await rule_check_arm_service.arm_rule_check(arm_input, current_user, session)
