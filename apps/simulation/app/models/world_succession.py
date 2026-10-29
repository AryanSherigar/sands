from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.ids import FactionId, LeaderId, WholeNumber


class CrisisState(WorldModel):
    faction_id: FactionId
    ends_turn: WholeNumber
    regent_id: LeaderId
    heir_id: LeaderId | None = None
    heir_comes_of_age_turn: WholeNumber | None = None
    is_penalty_active: bool = True


class SuccessionWorldState(WorldModel):
    crises: list[CrisisState] = Field(default_factory=list)
