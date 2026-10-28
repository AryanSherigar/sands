from enum import Enum

from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.ids import (
    AmbitionId,
    ArmyId,
    CommanderId,
    EntityId,
    FactionId,
    GovernorId,
    LeaderId,
    Percent,
    RegionId,
    SignedPercent,
    TraitId,
    WholeNumber,
)


class OpinionReason(WorldModel):
    cause: str
    value: int
    fade_per_turn: WholeNumber


class OpinionState(WorldModel):
    target_id: LeaderId
    reasons: list[OpinionReason] = Field(default_factory=list)


class MemoryState(WorldModel):
    kind: str
    turn: WholeNumber
    subject_id: EntityId | None = None
    weight: int


class PlayerBeliefs(WorldModel):
    known_tactic_counts: dict[str, WholeNumber] = Field(default_factory=dict)
    believes_oathbreaker: bool = False
    mercy_score: SignedPercent = 0
    learning_progress: Percent = 0


class LeaderState(WorldModel):
    id: LeaderId
    name: str
    faction_id: FactionId
    trait_ids: list[TraitId] = Field(default_factory=list)
    ambition_ids: list[AmbitionId] = Field(default_factory=list)
    age: WholeNumber
    stress: Percent = 0
    is_alive: bool = True
    memories: list[MemoryState] = Field(default_factory=list)
    opinions: dict[LeaderId, OpinionState] = Field(default_factory=dict)
    beliefs: PlayerBeliefs = Field(default_factory=PlayerBeliefs)


class GovernorState(WorldModel):
    id: GovernorId
    name: str
    region_id: RegionId
    trait_ids: list[TraitId] = Field(default_factory=list)
    opinion_of_ruler: SignedPercent = 0


class CommanderStatus(str, Enum):
    ACTIVE = "active"
    CAPTURED = "captured"
    DEAD = "dead"


class CommanderState(WorldModel):
    id: CommanderId
    name: str
    faction_id: FactionId
    trait_ids: list[TraitId] = Field(default_factory=list)
    is_important: bool = False
    army_id: ArmyId | None = None
    status: CommanderStatus = CommanderStatus.ACTIVE
