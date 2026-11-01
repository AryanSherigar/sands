"""Authenticated, provider-free combat state and action endpoints."""

import uuid
from typing import Annotated

from app.db.connection import get_db_session
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.combat import (
    CombatActionRequest,
    CombatActionResult,
    CombatOptions,
    CombatOutcomeRequest,
    CombatOutcomeResult,
    CombatStartRequest,
    CombatStateView,
)
from app.routers.alpha_guards import forbid_when_turns_suspended
from app.services.combat_lifecycle_service import execute_lifecycle, get_combat_options
from app.services.combat_service import apply_combat_action, get_combat_state
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/v1/combat",
    tags=["Combat"],
    dependencies=[Depends(forbid_when_turns_suspended)],
)


@router.get("/{playthrough_id}/options")
async def read_options(
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CombatOptions:
    """Return eligible encounter choices and unresolved combat state."""
    return await get_combat_options(
        session, playthrough_id, participant_id, current_user
    )


@router.post("/start")
async def start_encounter(
    request: CombatStartRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CombatStateView:
    """Start a scenario-authorized encounter."""
    return await execute_lifecycle(session, request, current_user)


@router.post("/outcome")
async def resolve_outcome(
    request: CombatOutcomeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CombatOutcomeResult:
    """Apply the authored fallback after the player's defeat."""
    return await execute_lifecycle(session, request, current_user)


@router.get("/{playthrough_id}")
async def read_combat(
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CombatStateView:
    return await get_combat_state(session, playthrough_id, participant_id, current_user)


@router.post("/action")
async def submit_combat_action(
    request: CombatActionRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CombatActionResult:
    return await apply_combat_action(
        session,
        request.playthrough_id,
        request.participant_id,
        current_user,
        request.action,
    )
