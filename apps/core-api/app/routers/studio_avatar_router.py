"""Studio Avatar FastAPI router.

Handles prompt optimization and avatar asset generation endpoints for Scenario Studio.
"""

import io
import uuid
from typing import Annotated

from app.db.models.user import User
from app.integrations import storage_client
from app.middleware.auth import get_current_user
from app.models.portrait_generation import GeneratedPortrait, PortraitGenerationRequest
from app.models.premade_avatar import PremadeAvatarList
from app.services.avatar_mesh_builder import (
    MAX_AVATAR_IMAGE_BYTES,
    build_mesh_avatar_package,
    decode_avatar_image,
)
from app.services.avatar_prompt_service import optimize_avatar_prompt
from app.services.portrait_service import PortraitService
from app.services.premade_avatars import list_premade_avatars
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from fastapi import APIRouter, Depends, HTTPException, status
from PIL import Image
from pydantic import BaseModel, Field

MAX_AVATAR_DESCRIPTION_LENGTH = 1000
MAX_AVATAR_DATA_URL_LENGTH = ((MAX_AVATAR_IMAGE_BYTES + 2) // 3) * 4 + 32

router = APIRouter(prefix="/v1/studio/avatars", tags=["studio-avatars"])


class OptimizePromptRequest(BaseModel):
    description: str = Field(default="", max_length=MAX_AVATAR_DESCRIPTION_LENGTH)


class OptimizePromptResponse(BaseModel):
    optimized_prompt: str


class BuildMeshRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    image_url: str = Field(max_length=MAX_AVATAR_DATA_URL_LENGTH)


class BuildMeshResponse(BaseModel):
    avatar_url: str
    portrait_url: str
    name: str


@router.post(
    "/optimize-prompt",
    response_model=OptimizePromptResponse,
    status_code=status.HTTP_200_OK,
)
async def optimize_prompt_endpoint(
    req: OptimizePromptRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> OptimizePromptResponse:
    prompt = await optimize_avatar_prompt(req.description)
    return OptimizePromptResponse(optimized_prompt=prompt)


@router.get(
    "/premade",
    response_model=PremadeAvatarList,
    status_code=status.HTTP_200_OK,
)
async def list_premade_avatars_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
) -> PremadeAvatarList:
    """List the built-in animated avatars a creator can attach without generating one."""
    return PremadeAvatarList(avatars=list_premade_avatars())


def get_portrait_service(
    quota_service: Annotated[QuotaService, Depends(get_quota_service)],
) -> PortraitService:
    return PortraitService(quota_service)


@router.post(
    "/generate-portrait",
    response_model=GeneratedPortrait,
    status_code=status.HTTP_200_OK,
)
async def generate_portrait_endpoint(
    req: PortraitGenerationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PortraitService, Depends(get_portrait_service)],
) -> GeneratedPortrait:
    """Generate a leader portrait with Muse Image for the creator to review."""
    return await service.generate_portrait(req.prompt, current_user)


@router.post(
    "/build-mesh",
    response_model=BuildMeshResponse,
    status_code=status.HTTP_200_OK,
)
async def build_mesh_endpoint(
    req: BuildMeshRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> BuildMeshResponse:
    try:
        image_bytes = decode_avatar_image(req.image_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    mavatar_bytes = build_mesh_avatar_package(image_bytes, req.name)
    asset_id = uuid.uuid4()
    object_key = f"avatars/{asset_id}.mavatar"
    avatar_url = await storage_client.upload_public_bytes(
        object_key, mavatar_bytes, "application/zip"
    )
    with Image.open(io.BytesIO(image_bytes)) as portrait:
        output = io.BytesIO()
        portrait.convert("RGBA").save(output, format="PNG")
    try:
        portrait_url = await storage_client.upload_public_bytes(
            f"avatars/{asset_id}.png", output.getvalue(), "image/png"
        )
    except Exception:
        await storage_client.delete_object(avatar_url)
        raise
    return BuildMeshResponse(
        avatar_url=avatar_url, portrait_url=portrait_url, name=req.name
    )
