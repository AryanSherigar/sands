from app.models.base import WorldModel
from app.models.world_region import RegionIntel
from strategy_contracts.ids import FactionId, Percent, RegionId, WholeNumber


class MapScoutReport(WorldModel):
    id: str
    observer_faction_id: FactionId
    target_region_id: RegionId
    observed_turn: WholeNumber
    coverage_percent: Percent
    owner_id: FactionId | None = None
    garrison_estimate: RegionIntel | None = None
    is_accurate: bool
