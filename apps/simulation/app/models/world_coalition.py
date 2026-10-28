from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.ids import FactionId, WholeNumber


class ConquestRecord(WorldModel):
    turn: WholeNumber
    faction_id: FactionId
    wealth: WholeNumber


class CoalitionState(WorldModel):
    id: str
    target_id: FactionId
    member_ids: list[FactionId] = Field(default_factory=list)
    formed_turn: WholeNumber
    expires_turn: WholeNumber


class CoalitionWorldState(WorldModel):
    coalitions: list[CoalitionState] = Field(default_factory=list)
    conquests: list[ConquestRecord] = Field(default_factory=list)
    atrocities: dict[FactionId, WholeNumber] = Field(default_factory=dict)
