from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from app.models.base import WorldModel
from app.models.battle_command import Command
from app.models.battle_intelligence import BattleIntent
from app.models.battle_progress import OperationGuard
from app.models.stance import StanceChoice
from pydantic import Field, model_validator
from strategy_contracts.scene import (
    RefusedDemand,
    SceneOutcome,
    SceneType,
    TermsResult,
)
from strategy_contracts.terms import TermsCard


class ReplayStepKind(str, Enum):
    ACCEPT_COMMAND = "accept_command"
    CANCEL_COMMAND = "cancel_command"
    BEGIN_CAMPAIGN = "begin_campaign"
    ADVANCE_CAMPAIGN = "advance_campaign"
    RESUME_ECONOMY = "resume_economy"
    BEGIN_NEGOTIATION = "begin_negotiation"
    RESOLVE_NEGOTIATION = "resolve_negotiation"
    RESOLVE_SCENE = "resolve_scene"


class AcceptCommandReplayInput(WorldModel):
    kind: Literal[ReplayStepKind.ACCEPT_COMMAND] = ReplayStepKind.ACCEPT_COMMAND
    actor_id: str
    guard: OperationGuard
    command: Command


class CancelCommandReplayInput(WorldModel):
    kind: Literal[ReplayStepKind.CANCEL_COMMAND] = ReplayStepKind.CANCEL_COMMAND
    guard: OperationGuard
    command_id: str = Field(min_length=1, max_length=256)


class BeginCampaignReplayInput(WorldModel):
    kind: Literal[ReplayStepKind.BEGIN_CAMPAIGN] = ReplayStepKind.BEGIN_CAMPAIGN
    guard: OperationGuard
    stances: list[StanceChoice] = Field(default_factory=list)


class AdvanceCampaignReplayInput(WorldModel):
    kind: Literal[ReplayStepKind.ADVANCE_CAMPAIGN] = ReplayStepKind.ADVANCE_CAMPAIGN
    guard: OperationGuard
    intents: list[BattleIntent] = Field(default_factory=list)
    stances: list[StanceChoice] = Field(default_factory=list)


class ResumeEconomyReplayInput(WorldModel):
    kind: Literal[ReplayStepKind.RESUME_ECONOMY] = ReplayStepKind.RESUME_ECONOMY
    guard: OperationGuard
    scene_id: UUID
    choice: Literal["shortfall_take_loan", "shortfall_default"]
    stances: list[StanceChoice] = Field(default_factory=list)


class BeginNegotiationReplayInput(WorldModel):
    kind: Literal[ReplayStepKind.BEGIN_NEGOTIATION] = ReplayStepKind.BEGIN_NEGOTIATION
    guard: OperationGuard
    counterpart_faction_id: str = Field(min_length=1, max_length=128)


class ResolveNegotiationReplayInput(WorldModel):
    kind: Literal[ReplayStepKind.RESOLVE_NEGOTIATION] = (
        ReplayStepKind.RESOLVE_NEGOTIATION
    )
    guard: OperationGuard
    scene_id: UUID
    terms_card: TermsCard | None = None
    result: TermsResult | None = None
    refused_demand: RefusedDemand | None = None


class ResolveSceneReplayInput(WorldModel):
    kind: Literal[ReplayStepKind.RESOLVE_SCENE] = ReplayStepKind.RESOLVE_SCENE
    guard: OperationGuard
    scene_id: UUID
    scene_type: SceneType
    outcome: SceneOutcome


ReplayInput = Annotated[
    AcceptCommandReplayInput
    | CancelCommandReplayInput
    | BeginCampaignReplayInput
    | AdvanceCampaignReplayInput
    | ResumeEconomyReplayInput
    | BeginNegotiationReplayInput
    | ResolveNegotiationReplayInput
    | ResolveSceneReplayInput,
    Field(discriminator="kind"),
]


class ReplayStep(WorldModel):
    playthrough_id: UUID
    sequence: int = Field(ge=1)
    operation_id: str = Field(min_length=1, max_length=128)
    kind: ReplayStepKind
    input: ReplayInput
    before_hash: str = Field(min_length=1)
    after_hash: str = Field(min_length=1)
    turn: int = Field(ge=0)
    wave: int = Field(ge=0, le=4)

    @model_validator(mode="after")
    def validate_kind_matches_input(self) -> "ReplayStep":
        if self.kind.value != self.input.kind.value:
            raise ValueError("replay step kind must match its input")
        return self


def ordered_replay_steps(steps: list[ReplayStep]) -> list[ReplayStep]:
    ordered = sorted(steps, key=lambda step: step.sequence)
    expected = list(range(1, len(ordered) + 1))
    if [step.sequence for step in ordered] != expected:
        raise ValueError("replay steps must form a gapless sequence")
    return ordered
