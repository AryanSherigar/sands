from enum import Enum

from app.models.base import WorldModel
from strategy_contracts.enums import RouteStyle
from strategy_contracts.ids import RegionId, WholeNumber


class WarningKind(str, Enum):
    CLOSED_BORDER = "closed_border"
    ENEMY_TERRITORY = "enemy_territory"
    HOSTILE_ARMY = "hostile_army"


class RouteWarning(WorldModel):
    kind: WarningKind
    region_id: RegionId


class RoutePreview(WorldModel):
    styles: list[RouteStyle]
    route: list[RegionId]
    is_turning_back: bool
    base_cost: WholeNumber
    estimated_turns: WholeNumber
    warnings: list[RouteWarning]
