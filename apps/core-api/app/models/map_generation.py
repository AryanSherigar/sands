"""Pydantic models for strategy map generation endpoints."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MIN_DESCRIPTION_CHARS = 3
MAX_DESCRIPTION_CHARS = 500

MapDescription = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=MIN_DESCRIPTION_CHARS,
        max_length=MAX_DESCRIPTION_CHARS,
    ),
]


class MapGenerationRequest(BaseModel):
    """Creator's description of the world to draw."""

    description: MapDescription


class GeneratedRegionImage(BaseModel):
    """Stored flat-color region image, ready for the browser tracer."""

    region_image_url: str
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)


class GeneratedMapArt(BaseModel):
    """Stored painted picture, resized to match its region image."""

    picture_url: str
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)


class MapGenerationJobResponse(BaseModel):
    """Status and result of a background map generation job."""

    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    scenario_id: uuid.UUID
    status: Literal["pending", "running", "succeeded", "failed"]
    description: str
    region_image_url: str | None = None
    picture_url: str | None = None
    width: int | None = None
    height: int | None = None
    has_art: bool = False
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
