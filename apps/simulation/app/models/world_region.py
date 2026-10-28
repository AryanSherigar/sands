from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.enums import ImprovementKind
from strategy_contracts.ids import (
    FactionId,
    FaithId,
    GovernorId,
    Percent,
    RegionId,
    WholeNumber,
)


class ImprovementState(WorldModel):
    kind: ImprovementKind
    turns_remaining: WholeNumber


class OccupationState(WorldModel):
    occupier_id: FactionId
    siege_progress: WholeNumber


class RegionIntel(WorldModel):
    last_seen_turn: WholeNumber
    owner_id: FactionId | None
    garrison_low: WholeNumber
    garrison_high: WholeNumber


class RegionState(WorldModel):
    id: RegionId
    owner_id: FactionId | None
    population: WholeNumber
    wealth: WholeNumber
    manpower: WholeNumber
    unrest: Percent
    garrison: WholeNumber
    faith_id: FaithId | None
    improvements: list[ImprovementState] = Field(default_factory=list)
    governor_id: GovernorId | None = None
    claimant_ids: list[FactionId] = Field(default_factory=list)
    occupation: OccupationState | None = None
    conversion_turns_remaining: WholeNumber = 0
