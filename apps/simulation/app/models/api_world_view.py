from enum import Enum
from uuid import UUID

from app.models.base import WorldModel
from app.models.orders import QueuedOrder
from app.models.world_clock import TurnClock
from app.models.world_diplomacy import WarSide
from app.models.world_events import EndingState, PendingBattle
from app.models.world_faction import LoanState
from app.models.world_internal import UprisingResponse, UprisingState
from app.models.world_player import PlayerRuler
from app.models.world_region import RegionState
from pydantic import Field
from strategy_contracts.alliance import AllianceType
from strategy_contracts.conditions import ConditionScope
from strategy_contracts.enums import RelationStatus, TaxRate, Terrain, TroopType
from strategy_contracts.events import EffectKind
from strategy_contracts.ids import (
    ArmyId,
    EntityId,
    EventId,
    FactionId,
    LeaderId,
    Percent,
    RegionId,
    SignedPercent,
    WholeNumber,
)
from strategy_contracts.peace import PeaceTier
from strategy_contracts.pressure import PressureBand, RumorTopic
from strategy_contracts.scene import SceneType
from strategy_contracts.summary import SummaryAvailability
from strategy_contracts.vassal import DemandKind


class Visibility(str, Enum):
    VISIBLE = "visible"
    FOGGED = "fogged"


class IntRange(WorldModel):
    low: int
    high: int


class RegionView(WorldModel):
    region_id: RegionId
    owner_id: FactionId | None
    terrain: Terrain
    visibility: Visibility
    last_seen_turn: WholeNumber | None = None
    garrison_estimate: IntRange | None = None
    detail: RegionState | None = None


class ArmyView(WorldModel):
    army_id: ArmyId
    owner_id: FactionId
    location_id: RegionId
    size_estimate: IntRange | None = None
    troops: dict[TroopType, WholeNumber] | None = None
    commander_name: str | None = None


class RivalView(WorldModel):
    faction_id: FactionId
    name: str
    leader_name: str | None
    relation: RelationStatus
    treasury_range: IntRange
    manpower_range: IntRange


class OwnFactionView(WorldModel):
    id: FactionId
    leader_id: LeaderId | None
    treasury: int
    manpower: WholeNumber
    stability: Percent
    war_exhaustion: Percent
    reputation: SignedPercent
    tax_rate: TaxRate
    loans: list[LoanState] = Field(default_factory=list)


class PactView(WorldModel):
    commitment_id: str
    faction_a: FactionId
    faction_b: FactionId
    start_turn: WholeNumber
    end_turn: WholeNumber


class SceneRef(WorldModel):
    scene_id: UUID
    scene_type: SceneType


class EffectPreview(WorldModel):
    kind: EffectKind
    amount: int


class UprisingResponseView(WorldModel):
    id: UprisingResponse
    order_cost: int
    effects: list[EffectPreview] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    is_affordable: bool


class UprisingView(UprisingState):
    responses: list[UprisingResponseView] = Field(default_factory=list)
    turns_until_change: WholeNumber = 0
    is_final_stage: bool = False
    is_easing: bool = False
    rebel_troops: WholeNumber | None = None
    queued_response: UprisingResponse | None = None
    queued_command_id: str | None = None


class EventChoiceView(WorldModel):
    id: EntityId
    label_hint: str
    order_cost: int
    effects: list[EffectPreview] = Field(default_factory=list)
    is_affordable: bool


class PendingEventView(WorldModel):
    id: str
    template_id: EventId
    name: str
    subject_kind: ConditionScope
    subject_id: EntityId
    subject_name: str
    region_id: RegionId | None = None
    tier: WholeNumber
    max_tier: WholeNumber
    created_turn: WholeNumber
    deadline_turn: WholeNumber
    cause_key: str
    cause_inputs: dict[str, int] = Field(default_factory=dict)
    choices: list[EventChoiceView]
    neglect_effects: list[EffectPreview] = Field(default_factory=list)
    queued_choice_id: EntityId | None = None
    queued_command_id: str | None = None


class EventMemoryView(WorldModel):
    template_id: EventId
    name: str
    subject_id: EntityId
    subject_name: str
    region_id: RegionId | None = None
    last_tier: WholeNumber
    max_tier: WholeNumber
    scar: WholeNumber


class QueuedOrderView(QueuedOrder):
    is_cancellable: bool = False


class OwnPressureView(WorldModel):
    will_band: PressureBand
    strain_band: PressureBand
    will_factors: dict[str, int] = Field(default_factory=dict)
    strain_factors: dict[str, int] = Field(default_factory=dict)


class RumorView(WorldModel):
    about_faction_id: FactionId
    topic: RumorTopic
    band: PressureBand
    line_key: str
    turn: WholeNumber


class TruceView(WorldModel):
    faction_a: FactionId
    faction_b: FactionId
    tier: PeaceTier | None = None
    expires_turn: WholeNumber | None = None
    is_fragile: bool = False
    guarantor_ids: list[FactionId] = Field(default_factory=list)


class CoalitionView(WorldModel):
    id: str
    target_id: FactionId
    member_ids: list[FactionId]
    expires_turn: WholeNumber


class OwnThreatView(WorldModel):
    band: PressureBand
    factors: dict[str, int] = Field(default_factory=dict)


class AllianceView(WorldModel):
    id: str
    partner_id: FactionId
    alliance_type: AllianceType
    ends_turn: WholeNumber | None = None
    is_separate_peace_banned: bool = False


class CallView(WorldModel):
    id: str
    caller_id: FactionId
    war_id: str
    side: WarSide
    is_defensive: bool
    deadline_turn: WholeNumber


class VassalageView(WorldModel):
    id: str
    overlord_id: FactionId
    vassal_id: FactionId
    tribute_share_percent: int
    levy_share_percent: int
    is_foreign_policy_controlled: bool
    has_garrison_rights: bool
    ends_turn: WholeNumber | None = None


class PendingDemandView(WorldModel):
    id: str
    overlord_id: FactionId
    kind: DemandKind
    amount: WholeNumber
    granted: WholeNumber
    deadline_turn: WholeNumber


class HostageView(WorldModel):
    id: str
    giver_id: FactionId
    holder_id: FactionId
    leader_id: LeaderId
    release_turn: WholeNumber
    is_at_mercy: bool = False


class MediationOfferView(WorldModel):
    id: str
    mediator_id: FactionId
    war_id: str
    expires_turn: WholeNumber


class WorldView(WorldModel):
    summary_availability: SummaryAvailability = Field(
        default_factory=SummaryAvailability
    )
    clock: TurnClock
    my_faction: OwnFactionView
    ruler: PlayerRuler
    regions: list[RegionView] = Field(default_factory=list)
    armies: list[ArmyView] = Field(default_factory=list)
    rivals: list[RivalView] = Field(default_factory=list)
    pacts: list[PactView] = Field(default_factory=list)
    queued_orders: list[QueuedOrderView] = Field(default_factory=list)
    orders_remaining: int
    pending_events: list[PendingEventView] = Field(default_factory=list)
    event_memories: list[EventMemoryView] = Field(default_factory=list)
    pending_battles: list[PendingBattle] = Field(default_factory=list)
    uprisings: list[UprisingView] = Field(default_factory=list)
    own_pressure: OwnPressureView | None = None
    rumors: list[RumorView] = Field(default_factory=list)
    truces: list[TruceView] = Field(default_factory=list)
    own_hostages: list[HostageView] = Field(default_factory=list)
    open_mediations: list[MediationOfferView] = Field(default_factory=list)
    alliances: list[AllianceView] = Field(default_factory=list)
    pending_calls: list[CallView] = Field(default_factory=list)
    vassalages: list[VassalageView] = Field(default_factory=list)
    coalitions: list[CoalitionView] = Field(default_factory=list)
    own_threat: OwnThreatView | None = None
    pending_demands: list[PendingDemandView] = Field(default_factory=list)
    pending_scene: SceneRef | None = None
    ending: EndingState | None = None
