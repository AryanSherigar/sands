from enum import Enum
from typing import Literal
from uuid import UUID

from app.models.base import WorldModel
from pydantic import (
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.enums import RelationStatus, TroopType
from strategy_contracts.ids import (
    EntityId,
    FactionId,
    LeaderId,
    RegionId,
    WholeNumber,
)
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scene import OutrageLevel
from strategy_contracts.terms import Term


class RelationState(WorldModel):
    faction_a: FactionId
    faction_b: FactionId
    status: RelationStatus
    since_turn: WholeNumber

    @model_validator(mode="after")
    def validate_sorted_pair(self) -> "RelationState":
        if self.faction_a >= self.faction_b:
            raise ValueError("relation faction ids must be stored sorted and distinct")
        return self


class TruceState(WorldModel):
    id: str = ""
    faction_a: FactionId
    faction_b: FactionId
    expires_turn: WholeNumber = 0
    signed_turn: WholeNumber = 0
    tier: PeaceTier | None = None
    guarantor_ids: list[FactionId] = Field(default_factory=list)
    signatory_leader_ids: list[LeaderId] = Field(default_factory=list)
    is_fragile: bool = False
    origin_war_id: str | None = None
    loser_id: FactionId | None = None
    harshness: WholeNumber = 0
    ceded_region_ids: list[RegionId] = Field(default_factory=list)


class CommitmentStatus(str, Enum):
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    BREACHED = "breached"
    EXPIRED = "expired"


class CommitmentState(WorldModel):
    id: str
    term: Term
    start_turn: WholeNumber
    end_turn: WholeNumber | None = None
    status: CommitmentStatus = CommitmentStatus.ACTIVE
    origin_scene_id: UUID | None = None


class OathbreakerMark(WorldModel):
    faction_id: FactionId
    since_turn: WholeNumber


class DiplomaticPlayState(WorldModel):
    id: str
    attacker_id: FactionId
    defender_id: FactionId
    demands: list[Term] = Field(default_factory=list)
    stage: Literal["demand", "counter", "resolved"]
    scene_id: UUID | None = None
    due_turn: WholeNumber = 0
    kind: Literal["demand", "talks"] = "demand"


class GroundState(WorldModel):
    id: str
    kind: GroundKind
    holder_faction_id: FactionId
    holder_leader_id: LeaderId
    target_faction_id: FactionId
    region_id: RegionId | None = None
    strength: WholeNumber
    since_turn: WholeNumber
    is_personal: bool
    is_forged: bool = False
    matures_turn: WholeNumber | None = None
    suspect_level: WholeNumber = 0

    @model_validator(mode="after")
    def validate_claim_has_region(self) -> "GroundState":
        if self.kind == GroundKind.CLAIM and self.region_id is None:
            raise ValueError("a claim ground names its region")
        return self


class WarSide(str, Enum):
    ATTACKER = "attacker"
    DEFENDER = "defender"


class WarGoalState(WorldModel):
    faction_id: FactionId
    kind: GroundKind
    region_id: RegionId | None = None


class WarState(WorldModel):
    id: str
    attacker_id: FactionId
    defender_id: FactionId
    participant_ids: list[FactionId] = Field(default_factory=list)
    war_score_attacker: WholeNumber = 0
    war_score_defender: WholeNumber = 0
    started_turn: WholeNumber
    ground_kind: GroundKind | None = None
    goals: list[WarGoalState] = Field(default_factory=list)
    is_surprise: bool = False
    scored_battle_ids: list[str] = Field(default_factory=list)
    battle_points_attacker: WholeNumber = 0
    battle_points_defender: WholeNumber = 0
    prisoner_points_attacker: WholeNumber = 0
    prisoner_points_defender: WholeNumber = 0
    side_by_faction: dict[FactionId, WarSide] = Field(default_factory=dict)

    @model_serializer(mode="wrap")
    def omit_empty_side_map(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        document = handler(self)
        if not document.get("side_by_faction"):
            document.pop("side_by_faction", None)
        return document


class OutrageState(WorldModel):
    faction_id: FactionId
    level: OutrageLevel
    expires_turn: WholeNumber
    target_faction_id: FactionId | None = None
    mobilized_until_turn: WholeNumber = 0


class PrisonerKind(str, Enum):
    TROOPS = "troops"
    CHARACTER = "character"


class PrisonerState(WorldModel):
    id: str
    held_by_id: FactionId
    origin_faction_id: FactionId
    kind: PrisonerKind
    troop_count: WholeNumber = 0
    character_id: EntityId | None = None
    is_legacy_aggregate: bool = False
    origin_battle_id: str | None = None
    troops_by_type: dict[TroopType, WholeNumber] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_prisoner_kind(self) -> "PrisonerState":
        if self.is_legacy_aggregate:
            return self._validate_legacy_aggregate()
        if self.kind == PrisonerKind.TROOPS:
            if self.origin_battle_id is None or not self.troops_by_type:
                raise ValueError("troop captives require battle origin and troop types")
            if self.character_id is not None:
                raise ValueError("troop captives cannot identify a character")
            if self.troop_count != sum(self.troops_by_type.values()):
                raise ValueError("troop_count must equal troop type total")
            return self
        if self.character_id is None:
            raise ValueError("character captive requires character id")
        if self.troop_count or self.troops_by_type or self.origin_battle_id:
            raise ValueError("character captive cannot contain troop fields")
        return self

    def _validate_legacy_aggregate(self) -> "PrisonerState":
        if self.kind != PrisonerKind.TROOPS or self.character_id is not None:
            raise ValueError("legacy aggregate must be a troop captive")
        if self.origin_battle_id is not None or self.troops_by_type:
            raise ValueError("legacy aggregate has unknown origin and composition")
        return self


class EnvoyState(WorldModel):
    id: str
    from_faction_id: FactionId
    at_faction_id: FactionId
    character_id: EntityId | None = None
