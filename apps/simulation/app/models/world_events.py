from enum import Enum
from typing import Literal
from uuid import UUID

from app.models.base import WorldModel
from app.models.world_battle import BattleState
from pydantic import Field, SerializerFunctionWrapHandler, model_serializer
from strategy_contracts.conditions import ConditionScope
from strategy_contracts.endings import EndingGrade
from strategy_contracts.ids import (
    EndingId,
    EntityId,
    EventId,
    FactionId,
    WholeNumber,
)
from strategy_contracts.overtures import OvertureKind
from strategy_contracts.scenario import EndingKind
from strategy_contracts.summary import SummaryFact
from strategy_contracts.terms import TermsCard

MAX_CAMPAIGN_WAVES = 4


class PhaseName(str, Enum):
    ORDERS = "orders"
    DIPLOMACY = "diplomacy"
    MOVEMENT = "movement"
    BATTLES = "battles"
    SIEGES = "sieges"
    ECONOMY = "economy"
    INTERNAL = "internal"
    TIME = "time"
    EVENTS = "events"
    STORY_CHECK = "story_check"


class TurnStatus(str, Enum):
    RESOLVED = "resolved"
    PAUSED = "paused"
    AWAITING_COMMANDS = "awaiting_commands"


PHASE_ORDER: tuple[PhaseName, ...] = (
    PhaseName.ORDERS,
    PhaseName.DIPLOMACY,
    PhaseName.MOVEMENT,
    PhaseName.BATTLES,
    PhaseName.SIEGES,
    PhaseName.ECONOMY,
    PhaseName.INTERNAL,
    PhaseName.TIME,
    PhaseName.EVENTS,
    PhaseName.STORY_CHECK,
)


class EventCause(WorldModel):
    summary_key: str
    subject_ids: list[EntityId] = Field(default_factory=list)
    inputs: dict[str, int] = Field(default_factory=dict)


class StateChange(WorldModel):
    path: str
    before: int | str | None = None
    after: int | str | None = None


class EventLogEntry(WorldModel):
    seq: WholeNumber
    turn: WholeNumber
    phase: PhaseName
    kind: str
    is_major: bool = False
    significance: WholeNumber = 0
    cause: EventCause
    changes: list[StateChange] = Field(default_factory=list)


class PendingEvent(WorldModel):
    id: str
    template_id: EventId
    choice_ids: list[EntityId]
    subject_kind: ConditionScope
    subject_id: EntityId
    subject_name: str
    tier: WholeNumber
    created_turn: WholeNumber
    deadline_turn: WholeNumber
    cause_key: str
    cause_inputs: dict[str, int] = Field(default_factory=dict)
    scene_id: UUID | None = None


PendingBattle = BattleState


class SignificanceTracker(WorldModel):
    points: WholeNumber = 0
    last_summary_turn: WholeNumber = 0


class Overture(WorldModel):
    kind: OvertureKind
    card: TermsCard | None = None
    pretext: str
    truce_id: str | None = None


class PendingNegotiation(WorldModel):
    trigger_id: EntityId
    initiator_faction_id: FactionId
    is_declinable: bool
    cooldown_until_turn: WholeNumber
    overture: Overture | None = None

    @model_serializer(mode="wrap")
    def omit_absent_overture(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        document = handler(self)
        if document.get("overture") is None:
            document.pop("overture", None)
        return document


class SummaryRequest(WorldModel):
    """A player-safe chronicle input envelope; prose delivery is a later adapter."""

    id: str
    requested_turn: WholeNumber
    event_seqs: list[WholeNumber] = Field(default_factory=list)
    trigger: Literal["major_event", "significance"]
    facts: list[SummaryFact] = Field(default_factory=list)

    @model_serializer(mode="wrap")
    def omit_empty_facts(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        document = handler(self)
        if not self.facts:
            document.pop("facts", None)
        return document


class PendingSummaryFact(WorldModel):
    seq: WholeNumber
    fact: SummaryFact
    significance: WholeNumber = 0


class TurnProgress(WorldModel):
    phase: PhaseName | None = None
    pending_scene_id: UUID | None = None
    pending_negotiation: PendingNegotiation | None = None
    negotiation_counterpart_id: FactionId | None = None
    completed_waves: int = Field(default=0, ge=0, le=MAX_CAMPAIGN_WAVES)
    is_campaign_active: bool = False
    waiting_reason: (
        Literal["awaiting_commands", "awaiting_scene", "awaiting_battle_decision"]
        | None
    ) = None

    @model_serializer(mode="wrap")
    def preserve_legacy_progress(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        document = handler(self)
        defaults = {
            "pending_negotiation": None,
            "negotiation_counterpart_id": None,
            "completed_waves": 0,
            "is_campaign_active": False,
            "waiting_reason": None,
        }
        for key, default in defaults.items():
            if document.get(key) == default:
                document.pop(key, None)
        return document


class EndingState(WorldModel):
    ending_id: EndingId
    kind: EndingKind
    turn: WholeNumber
    grade: EndingGrade | None = None
    inputs: dict[str, int] = Field(default_factory=dict)

    @model_serializer(mode="wrap")
    def omit_ungraded_fields(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        document = handler(self)
        if self.grade is None:
            document.pop("grade", None)
        if not self.inputs:
            document.pop("inputs", None)
        return document
