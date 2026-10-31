"""Pydantic models for strategy map generation endpoints."""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

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
