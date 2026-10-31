from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.ids import ArmyId, FactionId, RegionId, WholeNumber


class SiegeState(WorldModel):
    region_id: RegionId
    besieger_id: FactionId
    army_ids: list[ArmyId] = Field(default_factory=list)
    progress: WholeNumber = 0
