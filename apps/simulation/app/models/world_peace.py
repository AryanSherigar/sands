from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.ids import FactionId, LeaderId, WholeNumber
from strategy_contracts.peace import PeaceTier


class HostageState(WorldModel):
    id: str
    giver_id: FactionId
    holder_id: FactionId
    leader_id: LeaderId
    release_turn: WholeNumber
    truce_id: str
    is_at_mercy: bool = False


class BreachPressureState(WorldModel):
    faction_a: FactionId
    faction_b: FactionId
    pressure: WholeNumber = 0
    last_grievance_turn: WholeNumber = 0


class TreatyLapse(WorldModel):
    truce_id: str
    faction_a: FactionId
    faction_b: FactionId
    original_tier: PeaceTier
    leader_id: LeaderId
    turn: WholeNumber


class PeaceState(WorldModel):
    hostages: list[HostageState] = Field(default_factory=list)
    breach: list[BreachPressureState] = Field(default_factory=list)
    lapses: list[TreatyLapse] = Field(default_factory=list)
    ransom_points: dict[str, WholeNumber] = Field(default_factory=dict)
