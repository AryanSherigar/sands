"""FastAPI router for master-mode rule check endpoints (tool `rule_checks`)."""

import uuid
from typing import Annotated

from app.db.connection import get_db_session
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.models.rule_check import (
    RuleCheckCreate,
    RuleCheckListResponse,
    RuleCheckReorderRequest,
    RuleCheckResponse,
    RuleCheckUpdate,
)
from app.repositories.entity_repo import EntityRepo
from app.repositories.rule_check_repo import RuleCheckRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.rule_check_service import RuleCheckService
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/v1/scenarios/{scenario_id}/rule-checks",
    tags=["Rule checks"],
)


def get_rule_check_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> RuleCheckService:
    return RuleCheckService(
        RuleCheckRepo(session), EntityRepo(session), ScenarioRepo(session)
    )


@router.post("", response_model=RuleCheckResponse, status_code=status.HTTP_201_CREATED)
async def create_rule_check(
    scenario_id: uuid.UUID,
    data: RuleCheckCreate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RuleCheckService, Depends(get_rule_check_service)],
) -> RuleCheckResponse:
    """Add a timed prompt to a master-mode scenario (requires the tool)."""
    return await service.create_check(scenario_id, user.user_id, data)


@router.get("", response_model=RuleCheckListResponse, status_code=status.HTTP_200_OK)
async def list_rule_checks(
    scenario_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RuleCheckService, Depends(get_rule_check_service)],
) -> RuleCheckListResponse:
    """List a scenario's rule checks, priority-ordered."""
    items = await service.list_checks(scenario_id, user.user_id)
    return RuleCheckListResponse(items=items)


@router.post(
    "/reorder", response_model=RuleCheckListResponse, status_code=status.HTTP_200_OK
)
async def reorder_rule_checks(
    scenario_id: uuid.UUID,
    data: RuleCheckReorderRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RuleCheckService, Depends(get_rule_check_service)],
) -> RuleCheckListResponse:
    """Reassign priority to match the creator's chosen order."""
    items = await service.reorder_checks(
        scenario_id, user.user_id, data.ordered_check_ids
    )
    return RuleCheckListResponse(items=items)


@router.get(
    "/{check_id}", response_model=RuleCheckResponse, status_code=status.HTTP_200_OK
)
async def get_rule_check(
    scenario_id: uuid.UUID,
    check_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RuleCheckService, Depends(get_rule_check_service)],
) -> RuleCheckResponse:
    """Fetch a single rule check."""
    return await service.get_check(scenario_id, check_id, user.user_id)


@router.patch(
    "/{check_id}", response_model=RuleCheckResponse, status_code=status.HTTP_200_OK
)
async def update_rule_check(
    scenario_id: uuid.UUID,
    check_id: uuid.UUID,
    data: RuleCheckUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RuleCheckService, Depends(get_rule_check_service)],
) -> RuleCheckResponse:
    """Update a rule check's fields."""
    return await service.update_check(scenario_id, check_id, user.user_id, data)


@router.delete("/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule_check(
    scenario_id: uuid.UUID,
    check_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RuleCheckService, Depends(get_rule_check_service)],
) -> Response:
    """Remove a rule check."""
    await service.delete_check(scenario_id, check_id, user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
