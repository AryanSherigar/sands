"""FastAPI router for optional scenario tool endpoints."""

import uuid
from typing import Annotated

from app.db.connection import get_db_session
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.models.tools import ToolsResponse, ToolsUpdate
from app.repositories.scenario_repo import ScenarioRepo
from app.services.tool_service import ToolService
from app.tools.data_counters import count_tool_rows
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/v1/scenarios/{scenario_id}/tools",
    tags=["Tools"],
)


def get_tool_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> ToolService:
    async def count_rows(tool_key: str, scenario_id: uuid.UUID) -> int:
        return await count_tool_rows(session, tool_key, scenario_id)

    return ToolService(ScenarioRepo(session), count_rows)


@router.get("", response_model=ToolsResponse, status_code=status.HTTP_200_OK)
async def get_tools(
    scenario_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ToolService, Depends(get_tool_service)],
) -> ToolsResponse:
    """Return the scenario's enabled tools and any inert authored data."""
    return await service.get_tools(scenario_id, user.user_id)


@router.put("", response_model=ToolsResponse, status_code=status.HTTP_200_OK)
async def update_tools(
    scenario_id: uuid.UUID,
    data: ToolsUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ToolService, Depends(get_tool_service)],
) -> ToolsResponse:
    """Replace the scenario's enabled tools; required tools are auto-enabled."""
    return await service.update_tools(scenario_id, user.user_id, data)
