from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from app.models.base import WorldModel
from app.models.battle_intelligence import BattleIntent
from app.models.intent_briefing import IntentBriefing
from app.models.world_battle import BattleView
from app.models.world_player import PlayerRuler
from pydantic import Field, model_validator
from strategy_contracts.scenario import StrategyScenario


class OperationGuard(WorldModel):
    operation_id: str = Field(min_length=1, max_length=128)
    expected_world_version: int = Field(ge=1)
    expected_turn: int = Field(ge=0)
    expected_wave: int = Field(ge=0, le=4)


class InitializeCampaign(WorldModel):
    playthrough_id: UUID
    owner_user_id: UUID
    operation_id: str = Field(min_length=1, max_length=128)
    scenario: StrategyScenario
    ruler: PlayerRuler
    seed: int | None = None
    player_faction_id: str


CampaignStatus = Literal[
    "planning",
    "awaiting_commands",
    "awaiting_battle_decision",
    "awaiting_scene",
    "turn_completed",
]


class CampaignState(WorldModel):
    playthrough_id: UUID
    world_version: int
    world_hash: str
    turn: int
    wave: int
    orders_remaining: int
    status: CampaignStatus
    battles: list[BattleView] = Field(default_factory=list)
    scene_id: UUID | None = None


class MutationResponse(CampaignState):
    operation_id: str
    accepted_command_id: str | None = None


class OperationRow(WorldModel):
    playthrough_id: UUID
    actor_id: str
    operation_id: str
    request_hash: str
    route_kind: str
    status_code: int
    result_version: int
    response: MutationResponse
    committed_sequence: int
    created_at: datetime


class IntentRequestState(str, Enum):
    PENDING = "pending"
    LEASED = "leased"
    COMPLETED = "completed"
    FALLBACK = "fallback"
    ACTIVATED = "activated"


class IntentRequest(WorldModel):
    playthrough_id: UUID
    request_id: str
    battle_id: str
    faction_id: str
    campaign_turn: int = Field(ge=0)
    intended_wave: int = Field(ge=1, le=4)
    input_hash: str
    observation_fingerprint: str
    policy_version: str
    redacted_input: IntentBriefing
    fallback: BattleIntent
    candidate: BattleIntent | None = None
    state: IntentRequestState = IntentRequestState.PENDING
    attempts: int = Field(default=0, ge=0, le=1)
    lease_token: UUID | None = None
    lease_expires_at: datetime | None = None
    created_at: datetime | None = None

    @model_validator(mode="after")
    def validate_intent_identity(self) -> "IntentRequest":
        fields = (
            "battle_id",
            "faction_id",
            "campaign_turn",
            "intended_wave",
            "input_hash",
            "observation_fingerprint",
            "policy_version",
        )
        for intent in (self.fallback, self.candidate):
            if intent is not None and any(
                getattr(intent, name) != getattr(self, name) for name in fields
            ):
                raise ValueError("intent request identity must match recorded intent")
        if (
            self.redacted_input.battle.id != self.battle_id
            or self.redacted_input.faction_id != self.faction_id
        ):
            raise ValueError("intent request identity must match observer briefing")
        return self
