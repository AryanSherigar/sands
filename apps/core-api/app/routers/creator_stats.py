"""Creator-only stats endpoints."""

import uuid
from typing import Annotated

from app.db.connection import get_db_session
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.models.creator_stats import (
    DEFAULT_STATS_RANGE,
    CreatorStatsOverviewResponse,
    ScenarioStatsResponse,
    StatsRange,
)
from app.repositories.creator_stats_repo import CreatorStatsRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.creator_stats_service import CreatorStatsService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Creator Stats"])


def get_creator_stats_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> CreatorStatsService:
    return CreatorStatsService(CreatorStatsRepo(session), ScenarioRepo(session))


@router.get("/v1/creators/me/stats", response_model=CreatorStatsOverviewResponse)
async def get_creator_stats_overview(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreatorStatsService, Depends(get_creator_stats_service)],
    stats_range: Annotated[StatsRange, Query(alias="range")] = DEFAULT_STATS_RANGE,
) -> CreatorStatsOverviewResponse:
    """Stats across the caller's published and archived scenarios."""
    return await service.get_overview(user_id=user.user_id, stats_range=stats_range)


@router.get("/v1/scenarios/{scenario_id}/stats", response_model=ScenarioStatsResponse)
async def get_scenario_stats(
    scenario_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CreatorStatsService, Depends(get_creator_stats_service)],
    stats_range: Annotated[StatsRange, Query(alias="range")] = DEFAULT_STATS_RANGE,
) -> ScenarioStatsResponse:
    """Deep stats for one scenario. 404 unless the caller created it."""
    return await service.get_scenario_stats(
        scenario_id=scenario_id, user_id=user.user_id, stats_range=stats_range
    )
