"""FastAPI router for file upload endpoints."""

from typing import Annotated

from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.models.image_generation import CoverImageGenerationRequest
from app.models.upload import ImageUploadResponse
from app.routers.upload_reading import read_capped
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from app.services.upload_service import (
    MAX_COVER_IMAGE_BYTES,
    MAX_SCENARIO_AUDIO_BYTES,
    UploadService,
)
from fastapi import APIRouter, Depends, File, UploadFile, status

router = APIRouter(
    prefix="/v1/uploads",
    tags=["Uploads"],
)


def get_upload_service(
    quota_service: Annotated[QuotaService, Depends(get_quota_service)],
) -> UploadService:
    return UploadService(quota_service)


@router.post(
    "/scenario-cover-image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_scenario_cover_image(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
    file: Annotated[UploadFile, File()],
) -> ImageUploadResponse:
    """Upload a scenario cover image and return its public URL."""
    content = await read_capped(file, MAX_COVER_IMAGE_BYTES)
    url = await service.upload_cover_image(content, file.content_type or "")
    return ImageUploadResponse(url=url)


@router.post(
    "/avatar",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_avatar(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
    file: Annotated[UploadFile, File()],
) -> ImageUploadResponse:
    """Upload a user avatar image and return its public URL."""
    content = await read_capped(file, MAX_COVER_IMAGE_BYTES)
    url = await service.upload_avatar(content, file.content_type or "")
    return ImageUploadResponse(url=url)


@router.post(
    "/banner",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_banner(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
    file: Annotated[UploadFile, File()],
) -> ImageUploadResponse:
    """Upload a user profile banner image and return its public URL."""
    content = await read_capped(file, MAX_COVER_IMAGE_BYTES)
    url = await service.upload_banner(content, file.content_type or "")
    return ImageUploadResponse(url=url)


@router.post(
    "/scenario-map-image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_scenario_map_image(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
    file: Annotated[UploadFile, File()],
) -> ImageUploadResponse:
    """Upload a scenario map image and return its public URL."""
    content = await read_capped(file, MAX_COVER_IMAGE_BYTES)
    url = await service.upload_map_image(content, file.content_type or "")
    return ImageUploadResponse(url=url)


@router.post(
    "/scenario-audio",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_scenario_audio(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
    file: Annotated[UploadFile, File()],
) -> ImageUploadResponse:
    """Upload bounded MP3, OGG, or WAV audio for a Dodge encounter."""
    content = await read_capped(file, MAX_SCENARIO_AUDIO_BYTES)
    url = await service.upload_scenario_audio(content, file.content_type or "")
    return ImageUploadResponse(url=url)


@router.post(
    "/generate-cover-image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_scenario_cover_image(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
    body: CoverImageGenerationRequest,
) -> ImageUploadResponse:
    """Generate a scenario cover image with AI and return its public URL."""
    url = await service.generate_and_upload_cover_image(body, user)
    return ImageUploadResponse(url=url)
