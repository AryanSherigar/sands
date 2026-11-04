"""FastAPI router for private-scenario invite links and the allowlist."""

import uuid
from typing import Annotated

from app.db.connection import get_db_session
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.models.scenario_access import (
    ScenarioAccessMember,
    ScenarioInviteAcceptResponse,
    ScenarioInviteResponse,
)
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.scenario_invite_repo import ScenarioInviteRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.scenario_invite_service import ScenarioInviteService
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/v1",
    tags=["Scenario access"],
)


def get_scenario_invite_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> ScenarioInviteService:
    return ScenarioInviteService(
        ScenarioInviteRepo(session),
        ScenarioAccessRepo(session),
        ScenarioRepo(session),
    )


@router.post(
    "/scenarios/{scenario_id}/invites",
    response_model=ScenarioInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
    scenario_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ScenarioInviteService, Depends(get_scenario_invite_service)],
) -> ScenarioInviteResponse:
    """Mint a single-use invite link for the caller's own scenario."""
    return await service.create_invite(scenario_id, user.user_id)


@router.post(
    "/invites/{token}/accept",
    response_model=ScenarioInviteAcceptResponse,
    status_code=status.HTTP_200_OK,
)
async def accept_invite(
    token: str,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ScenarioInviteService, Depends(get_scenario_invite_service)],
) -> ScenarioInviteAcceptResponse:
    """Use an invite link: the caller joins the scenario's allowlist and the
    link is burned."""
    return await service.accept_invite(token, user.user_id)


@router.get(
    "/scenarios/{scenario_id}/access",
    response_model=list[ScenarioAccessMember],
    status_code=status.HTTP_200_OK,
)
async def list_access(
    scenario_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ScenarioInviteService, Depends(get_scenario_invite_service)],
) -> list[ScenarioAccessMember]:
    """List who may open the caller's private scenario besides the caller."""
    return await service.list_members(scenario_id, user.user_id)


@router.delete(
    "/scenarios/{scenario_id}/access/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_access(
    scenario_id: uuid.UUID,
    member_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ScenarioInviteService, Depends(get_scenario_invite_service)],
) -> Response:
    """Take a person off the caller's private scenario's allowlist."""
    await service.remove_member(scenario_id, user.user_id, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
