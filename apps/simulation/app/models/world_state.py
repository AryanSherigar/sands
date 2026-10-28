from enum import Enum
from uuid import UUID

from app.models.base import WorldModel
from app.models.battle_command import AcceptedCommand
from app.models.battle_intelligence import (
    BattleIntent,
    ReconReport,
    ScoutCapture,
    ScoutMission,
)
from app.models.world_ai import AimState
from app.models.world_alliance import AllianceWorldState
from app.models.world_army import ArmyState
from app.models.world_battle import BattleState, BattleStatus
from app.models.world_character import CommanderState, GovernorState, LeaderState
from app.models.world_clock import RngState, TurnClock
from app.models.world_coalition import CoalitionWorldState
from app.models.world_diplomacy import (
    CommitmentState,
    DiplomaticPlayState,
    EnvoyState,
    GroundState,
    OathbreakerMark,
    OutrageState,
    PrisonerState,
    RelationState,
    TruceState,
    WarState,
)
from app.models.world_endings import EndingsWorldState
from app.models.world_event_memory import EventMemory
from app.models.world_events import (
    EndingState,
    PendingEvent,
    PendingSummaryFact,
    SignificanceTracker,
    SummaryRequest,
    TurnProgress,
)
from app.models.world_faction import FactionState
from app.models.world_internal import UprisingState
from app.models.world_peace import PeaceState
from app.models.world_player import PlayerProfile, PlayerRuler
from app.models.world_pressure import PressureState
from app.models.world_region import RegionState
from app.models.world_vassal import VassalWorldState
from app.models.world_visibility import MapScoutReport
from pydantic import (
    AliasChoices,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)
from strategy_contracts.ids import (
    ArmyId,
    CommanderId,
    FactionId,
    GovernorId,
    LeaderId,
    RegionId,
)

WORLD_SCHEMA_VERSION = 6
LEGACY_VISIBILITY_RULESET = 0
CURRENT_VISIBILITY_RULESET = 1
CURRENT_BATTLE_CONTROL_RULESET = 1
CURRENT_INTERNAL_RULESET = 2
UPRISING_LIFECYCLE_RULESET = 2
CURRENT_LOGISTICS_RULESET = 1
CURRENT_SUMMARY_RULESET = 2
CURRENT_EVENTS_RULESET = 1
CURRENT_DIPLOMACY_RULESET = 1
CURRENT_PRESSURE_RULESET = 1
CURRENT_PEACE_RULESET = 1
CURRENT_ALLIANCE_RULESET = 1
CURRENT_VASSAL_RULESET = 1
CURRENT_COALITION_RULESET = 1
CURRENT_OUTRAGE_RULESET = 1
CURRENT_AI_RULESET = 2
CURRENT_ENDINGS_RULESET = 2
CURRENT_OVERTURE_RULESET = 1

LEGACY_OMISSIONS: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    ("battle_control_ruleset", 1, ("battle_control_ruleset",)),
    (
        "internal_ruleset",
        1,
        (
            "internal_ruleset",
            "battle_losses",
            "uprisings",
            "uprising_cooldowns",
        ),
    ),
    ("internal_ruleset", 2, ("region_grudges",)),
    ("logistics_ruleset", 1, ("logistics_ruleset", "supply_failure_turns")),
    (
        "summary_ruleset",
        1,
        ("summary_ruleset", "summary_event_cursor", "summary_requests"),
    ),
    ("summary_ruleset", 2, ("summary_pending_facts",)),
    ("events_ruleset", 1, ("events_ruleset", "event_memories")),
    ("diplomacy_ruleset", 1, ("diplomacy_ruleset", "grounds")),
    ("pressure_ruleset", 1, ("pressure_ruleset", "pressure")),
    ("peace_ruleset", 1, ("peace_ruleset", "peace")),
    ("alliance_ruleset", 1, ("alliance_ruleset", "alliance")),
    ("vassal_ruleset", 1, ("vassal_ruleset", "vassal")),
    ("coalition_ruleset", 1, ("coalition_ruleset", "coalition")),
    ("outrage_ruleset", 1, ("outrage_ruleset",)),
    ("ai_ruleset", 1, ("ai_ruleset",)),
    ("ai_ruleset", 2, ("aims",)),
    ("endings_ruleset", 1, ("endings_ruleset", "stability_collapse_turns")),
    ("endings_ruleset", 2, ("endings",)),
    (
        "overture_ruleset",
        1,
        ("overture_ruleset", "overture_cooldowns", "overture_renewals"),
    ),
)


class CounterKind(str, Enum):
    EVENT_SEQ = "event_seq"
    ARMY = "army"
    COMMITMENT = "commitment"
    PLAY = "play"
    WAR = "war"
    PRISONER = "prisoner"
    GROUND = "ground"
    TRUCE = "truce"
    HOSTAGE = "hostage"
    CALL = "call"
    COALITION = "coalition"
    DEMAND = "demand"
    ENVOY = "envoy"
    MEDIATION = "mediation"
    RUMOR = "rumor"
    PENDING_EVENT = "pending_event"
    BATTLE = "battle"
    LEADER = "leader"
    COMMANDER = "commander"


class WorldState(WorldModel):
    schema_version: int = WORLD_SCHEMA_VERSION
    visibility_ruleset: int = LEGACY_VISIBILITY_RULESET
    battle_control_ruleset: int = Field(default=0, ge=0, le=1)
    internal_ruleset: int = Field(default=0, ge=0, le=2)
    logistics_ruleset: int = Field(default=0, ge=0, le=1)
    summary_ruleset: int = Field(default=0, ge=0, le=2)
    events_ruleset: int = Field(default=0, ge=0, le=1)
    diplomacy_ruleset: int = Field(default=0, ge=0, le=1)
    pressure_ruleset: int = Field(default=0, ge=0, le=1)
    peace_ruleset: int = Field(default=0, ge=0, le=1)
    alliance_ruleset: int = Field(default=0, ge=0, le=1)
    vassal_ruleset: int = Field(default=0, ge=0, le=1)
    coalition_ruleset: int = Field(default=0, ge=0, le=1)
    outrage_ruleset: int = Field(default=0, ge=0, le=1)
    ai_ruleset: int = Field(default=0, ge=0, le=2)
    endings_ruleset: int = Field(default=0, ge=0, le=2)
    overture_ruleset: int = Field(default=0, ge=0, le=1)
    playthrough_id: UUID
    clock: TurnClock
    rng: RngState
    regions: dict[RegionId, RegionState] = Field(default_factory=dict)
    factions: dict[FactionId, FactionState] = Field(default_factory=dict)
    leaders: dict[LeaderId, LeaderState] = Field(default_factory=dict)
    governors: dict[GovernorId, GovernorState] = Field(default_factory=dict)
    commanders: dict[CommanderId, CommanderState] = Field(default_factory=dict)
    armies: dict[ArmyId, ArmyState] = Field(default_factory=dict)
    relations: list[RelationState] = Field(default_factory=list)
    truces: list[TruceState] = Field(default_factory=list)
    commitments: list[CommitmentState] = Field(default_factory=list)
    oathbreakers: list[OathbreakerMark] = Field(default_factory=list)
    plays: list[DiplomaticPlayState] = Field(default_factory=list)
    wars: list[WarState] = Field(default_factory=list)
    outrage: list[OutrageState] = Field(default_factory=list)
    prisoners: list[PrisonerState] = Field(default_factory=list)
    envoys: list[EnvoyState] = Field(default_factory=list)
    grounds: list[GroundState] = Field(default_factory=list)
    player_profile: PlayerProfile = Field(default_factory=PlayerProfile)
    ruler: PlayerRuler
    pending_events: list[PendingEvent] = Field(default_factory=list)
    event_memories: list[EventMemory] = Field(default_factory=list)
    battles: list[BattleState] = Field(
        default_factory=list,
        validation_alias=AliasChoices("battles", "pending_battles"),
    )
    accepted_commands: list[AcceptedCommand] = Field(default_factory=list)
    recon_reports: dict[str, ReconReport] = Field(default_factory=dict)
    scout_missions: dict[str, ScoutMission] = Field(default_factory=dict)
    scout_captures: dict[str, ScoutCapture] = Field(default_factory=dict)
    battle_intents: dict[str, BattleIntent] = Field(default_factory=dict)
    map_scout_reports: dict[str, MapScoutReport] = Field(default_factory=dict)
    battle_losses: dict[FactionId, int] = Field(default_factory=dict)
    uprisings: list[UprisingState] = Field(default_factory=list)
    uprising_cooldowns: dict[RegionId, int] = Field(default_factory=dict)
    region_grudges: dict[RegionId, int] = Field(default_factory=dict)
    supply_failure_turns: dict[ArmyId, int] = Field(default_factory=dict)
    summary_event_cursor: int = 0
    summary_requests: list[SummaryRequest] = Field(default_factory=list)
    summary_pending_facts: list[PendingSummaryFact] = Field(default_factory=list)
    significance: SignificanceTracker = Field(default_factory=SignificanceTracker)
    progress: TurnProgress = Field(default_factory=TurnProgress)
    counters: dict[CounterKind, int] = Field(default_factory=dict)
    ending: EndingState | None = None
    stability_collapse_turns: int = Field(default=0, ge=0)
    negotiation_cooldowns: dict[str, int] = Field(default_factory=dict)
    overture_cooldowns: dict[FactionId, int] = Field(default_factory=dict)
    overture_renewals: list[str] = Field(default_factory=list)
    aims: dict[FactionId, AimState] = Field(default_factory=dict)
    pressure: PressureState = Field(default_factory=PressureState)
    peace: PeaceState = Field(default_factory=PeaceState)
    alliance: AllianceWorldState = Field(default_factory=AllianceWorldState)
    vassal: VassalWorldState = Field(default_factory=VassalWorldState)
    coalition: CoalitionWorldState = Field(default_factory=CoalitionWorldState)
    endings: EndingsWorldState = Field(default_factory=EndingsWorldState)

    @model_serializer(mode="wrap")
    def preserve_legacy_control(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        document = handler(self)
        if not document.get("negotiation_cooldowns"):
            document.pop("negotiation_cooldowns", None)
        for ruleset, minimum, keys in LEGACY_OMISSIONS:
            if getattr(self, ruleset) < minimum:
                for key in keys:
                    document.pop(key, None)
        return document

    @property
    def pending_battles(self) -> list[BattleState]:
        """Compatibility access to the canonical battle store, including resolved metadata."""
        return self.battles

    @model_validator(mode="after")
    def validate_active_battle_membership(self) -> "WorldState":
        assigned_armies: set[str] = set()
        battle_ids: set[str] = set()
        for battle in self.battles:
            if battle.id in battle_ids:
                raise ValueError("battle ids must be unique")
            battle_ids.add(battle.id)
            if battle.status == BattleStatus.RESOLVED:
                continue
            members = set(battle.attacker_army_ids + battle.defender_army_ids)
            if assigned_armies & members:
                raise ValueError("army cannot belong to multiple active battles")
            assigned_armies.update(members)
        return self

    @model_validator(mode="after")
    def validate_contingent_ownership(self) -> "WorldState":
        for battle in self.battles:
            if battle.status != BattleStatus.RESOLVED:
                self._validate_battle_contingent_ownership(battle)
        return self

    def _validate_battle_contingent_ownership(self, battle: BattleState) -> None:
        memberships = (
            (contingent.faction_id, army_id)
            for contingent in battle.contingents.values()
            for army_id in contingent.army_ids
        )
        for faction_id, army_id in memberships:
            army = self.armies.get(army_id)
            if army is not None and army.owner_id != faction_id:
                raise ValueError("contingent faction must own its army")
