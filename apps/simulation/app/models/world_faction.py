from app.models.base import WorldModel
from app.models.world_region import RegionIntel
from pydantic import Field
from strategy_contracts.enums import TaxRate
from strategy_contracts.ids import (
    FactionId,
    LeaderId,
    Percent,
    RegionId,
    SignedPercent,
    WholeNumber,
)


class LoanState(WorldModel):
    principal: WholeNumber
    interest_percent: Percent
    turns_remaining: WholeNumber


class StanceState(WorldModel):
    option_id: str | None = None
    chosen_turn: WholeNumber = 0
    requested_for_turn: WholeNumber | None = None


class FactionState(WorldModel):
    id: FactionId
    leader_id: LeaderId | None
    capital_region_id: RegionId | None = None
    treasury: int
    stability: Percent
    war_exhaustion: Percent
    reputation: SignedPercent
    tax_rate: TaxRate
    loans: list[LoanState] = Field(default_factory=list)
    orders_remaining: int
    orders_debt: WholeNumber = 0
    credit_strikes: WholeNumber = 0
    turns_since_default: WholeNumber = 0
    stance: StanceState = Field(default_factory=StanceState)
    is_player: bool
    is_destroyed: bool = False
    intel: dict[RegionId, RegionIntel] = Field(default_factory=dict)
