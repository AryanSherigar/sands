"""FastAPI router for master-mode sheet rule endpoints (tool `rule_sheet`)."""

import uuid
from typing import Annotated

from app.db.connection import get_db_session
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.models.sheet_rule import (
    SheetRuleCreate,
    SheetRuleListResponse,
    SheetRuleReorderRequest,
    SheetRuleResponse,
    SheetRuleUpdate,
)
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.sheet_rule_repo import SheetRuleRepo
from app.services.sheet_rule_service import SheetRuleService
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/v1/scenarios/{scenario_id}/sheet-rules",
    tags=["Sheet rules"],
)


def get_sheet_rule_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> SheetRuleService:
    return SheetRuleService(SheetRuleRepo(session), ScenarioRepo(session))


@router.post("", response_model=SheetRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_sheet_rule(
    scenario_id: uuid.UUID,
    data: SheetRuleCreate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SheetRuleService, Depends(get_sheet_rule_service)],
) -> SheetRuleResponse:
    """Add a rule to a master-mode scenario's clipboard (requires the tool)."""
    return await service.create_rule(scenario_id, user.user_id, data)


@router.get("", response_model=SheetRuleListResponse, status_code=status.HTTP_200_OK)
async def list_sheet_rules(
    scenario_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SheetRuleService, Depends(get_sheet_rule_service)],
) -> SheetRuleListResponse:
    """List a scenario's sheet rules in clipboard order."""
    items = await service.list_rules(scenario_id, user.user_id)
    return SheetRuleListResponse(items=items)


@router.post(
    "/reorder", response_model=SheetRuleListResponse, status_code=status.HTTP_200_OK
)
async def reorder_sheet_rules(
    scenario_id: uuid.UUID,
    data: SheetRuleReorderRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SheetRuleService, Depends(get_sheet_rule_service)],
) -> SheetRuleListResponse:
    """Reassign display order to match the creator's chosen order."""
    items = await service.reorder_rules(
        scenario_id, user.user_id, data.ordered_rule_ids
    )
    return SheetRuleListResponse(items=items)


@router.get(
    "/{rule_id}", response_model=SheetRuleResponse, status_code=status.HTTP_200_OK
)
async def get_sheet_rule(
    scenario_id: uuid.UUID,
    rule_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SheetRuleService, Depends(get_sheet_rule_service)],
) -> SheetRuleResponse:
    """Fetch a single sheet rule."""
    return await service.get_rule(scenario_id, rule_id, user.user_id)


@router.patch(
    "/{rule_id}", response_model=SheetRuleResponse, status_code=status.HTTP_200_OK
)
async def update_sheet_rule(
    scenario_id: uuid.UUID,
    rule_id: uuid.UUID,
    data: SheetRuleUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SheetRuleService, Depends(get_sheet_rule_service)],
) -> SheetRuleResponse:
    """Update a sheet rule's fields."""
    return await service.update_rule(scenario_id, rule_id, user.user_id, data)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sheet_rule(
    scenario_id: uuid.UUID,
    rule_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SheetRuleService, Depends(get_sheet_rule_service)],
) -> Response:
    """Remove a sheet rule."""
    await service.delete_rule(scenario_id, rule_id, user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
