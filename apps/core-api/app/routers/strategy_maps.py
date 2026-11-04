"""FastAPI router for the strategy-mode region map."""

import uuid
from typing import Annotated

from app.db.connection import get_db_session, get_session_factory
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.models.map_generation import (
    GeneratedMapArt,
    GeneratedRegionImage,
    MapDescription,
    MapGenerationJobResponse,
    MapGenerationRequest,
)
from app.repositories.map_generation_job_repo import MapGenerationJobRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.routers.upload_reading import read_capped
from app.services.map_generation_service import (
    MAX_REGION_PNG_BYTES,
    MapGenerationService,
)
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from app.services.strategy_map_service import StrategyMapService
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from strategy_contracts.map import MapDocument

router = APIRouter(
    prefix="/v1/scenarios/{scenario_id}",
    tags=["Strategy Maps"],
)


def get_strategy_map_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> StrategyMapService:
    return StrategyMapService(ScenarioRepo(session))


def get_map_generation_service(
    quota_service: Annotated[QuotaService, Depends(get_quota_service)],
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> MapGenerationService:
    return MapGenerationService(quota_service, MapGenerationJobRepo(session))


@router.put("/strategy-map", response_model=MapDocument, status_code=status.HTTP_200_OK)
async def save_strategy_map(
    scenario_id: uuid.UUID,
    data: MapDocument,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[StrategyMapService, Depends(get_strategy_map_service)],
) -> MapDocument:
    """Validate and store the traced region map, replacing any earlier one."""
    return await service.save_map(scenario_id, user.user_id, data)


@router.get("/strategy-map", response_model=MapDocument, status_code=status.HTTP_200_OK)
async def get_strategy_map(
    scenario_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[StrategyMapService, Depends(get_strategy_map_service)],
) -> MapDocument:
    """Return the stored region map, or 404 if none has been saved."""
    return await service.get_map(scenario_id, user.user_id)


@router.post(
    "/strategy-map/generate-regions",
    response_model=GeneratedRegionImage,
    status_code=status.HTTP_200_OK,
)
async def generate_map_regions(
    scenario_id: uuid.UUID,
    data: MapGenerationRequest,
    user: Annotated[User, Depends(get_current_user)],
    map_service: Annotated[StrategyMapService, Depends(get_strategy_map_service)],
    service: Annotated[MapGenerationService, Depends(get_map_generation_service)],
) -> GeneratedRegionImage:
    """Draw a flat-color region image from a description and store it as a PNG."""
    await map_service.ensure_owner(scenario_id, user.user_id)
    return await service.generate_region_image(data.description, user)


@router.post(
    "/strategy-map/generate-art",
    response_model=GeneratedMapArt,
    status_code=status.HTTP_200_OK,
)
async def generate_map_art(
    scenario_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    description: Annotated[MapDescription, Form()],
    user: Annotated[User, Depends(get_current_user)],
    map_service: Annotated[StrategyMapService, Depends(get_strategy_map_service)],
    service: Annotated[MapGenerationService, Depends(get_map_generation_service)],
) -> GeneratedMapArt:
    """Paint a watercolor picture for an uploaded region image, at the same size."""
    await map_service.ensure_owner(scenario_id, user.user_id)
    region_png = await read_capped(file, MAX_REGION_PNG_BYTES)
    return await service.generate_art(region_png, description, user)


@router.post(
    "/strategy-map/generate",
    response_model=MapGenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_map(
    scenario_id: uuid.UUID,
    data: MapGenerationRequest,
    user: Annotated[User, Depends(get_current_user)],
    map_service: Annotated[StrategyMapService, Depends(get_strategy_map_service)],
    service: Annotated[MapGenerationService, Depends(get_map_generation_service)],
    background_tasks: BackgroundTasks,
    session_factory: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_session_factory)
    ],
) -> MapGenerationJobResponse:
    """Start map generation in the background; poll the job for its result."""
    await map_service.ensure_owner(scenario_id, user.user_id)
    job, is_new = await service.request_generation(scenario_id, user, data.description)
    if is_new:
        background_tasks.add_task(
            MapGenerationService.run_generation_job,
            job.job_id,
            session_factory,
            service.quota_service,
        )
    return job


@router.get(
    "/strategy-map/jobs/latest",
    response_model=MapGenerationJobResponse,
    status_code=status.HTTP_200_OK,
)
async def get_latest_map_job(
    scenario_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    map_service: Annotated[StrategyMapService, Depends(get_strategy_map_service)],
    service: Annotated[MapGenerationService, Depends(get_map_generation_service)],
) -> MapGenerationJobResponse:
    """Return the scenario's most recent map job, so the UI can resume after a reload."""
    await map_service.ensure_owner(scenario_id, user.user_id)
    return await service.get_latest_job(scenario_id, user.user_id)


@router.get(
    "/strategy-map/jobs/{job_id}",
    response_model=MapGenerationJobResponse,
    status_code=status.HTTP_200_OK,
)
async def get_map_job(
    scenario_id: uuid.UUID,
    job_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    map_service: Annotated[StrategyMapService, Depends(get_strategy_map_service)],
    service: Annotated[MapGenerationService, Depends(get_map_generation_service)],
) -> MapGenerationJobResponse:
    """Poll a submitted map generation job."""
    await map_service.ensure_owner(scenario_id, user.user_id)
    return await service.get_job_status(scenario_id, job_id, user.user_id)
