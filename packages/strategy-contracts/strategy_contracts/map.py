from enum import Enum

from pydantic import Field

from strategy_contracts.base import StrictModel
from strategy_contracts.enums import Terrain
from strategy_contracts.ids import RegionId
from strategy_contracts.limits import MAX_NAME_CHARS, MAX_OUTLINE_CHARS, MAX_REGIONS

MAP_SCHEMA_VERSION = 1


class MapSource(str, Enum):
    COLOR_IMAGE = "color_image"
    AZGAAR = "azgaar"
    MANUAL = "manual"


class Point(StrictModel):
    x: int
    y: int


class MapRegion(StrictModel):
    id: RegionId
    name: str = Field(min_length=1, max_length=MAX_NAME_CHARS)
    terrain: Terrain
    outline: str = Field(max_length=MAX_OUTLINE_CHARS)
    label_point: Point
    neighbor_ids: list[RegionId] = Field(default_factory=list)
    source_color: str | None = None
    source_ref: str | None = None


class Road(StrictModel):
    region_a: RegionId
    region_b: RegionId


class MapDocument(StrictModel):
    schema_version: int = MAP_SCHEMA_VERSION
    source: MapSource = MapSource.MANUAL
    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)
    image_url: str | None = None
    regions: list[MapRegion] = Field(default_factory=list, max_length=MAX_REGIONS)
    roads: list[Road] = Field(default_factory=list)
