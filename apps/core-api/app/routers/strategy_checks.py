"""FastAPI router for strategy-mode publish checks."""

import uuid
from typing import Annotated

from app.db.connection import get_db_session
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.repositories.scenario_repo import ScenarioRepo
from app.services.strategy_check_service import StrategyCheckService
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from strategy_contracts.publish_checks import PublishReport

router = APIRouter(
    prefix="/v1/scenarios/{scenario_id}",
    tags=["Strategy Checks"],
)


def get_strategy_check_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> StrategyCheckService:
    return StrategyCheckService(ScenarioRepo(session))


@router.post(
    "/strategy-check", response_model=PublishReport, status_code=status.HTTP_200_OK
)
async def check_strategy_scenario(
    scenario_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[StrategyCheckService, Depends(get_strategy_check_service)],
) -> PublishReport:
    """Return the blocking issues and warnings that publishing would raise."""
    return await service.check_scenario(scenario_id, user.user_id)
