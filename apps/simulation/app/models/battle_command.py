from enum import Enum
from typing import Annotated, Literal

from app.models.base import WorldModel
from app.models.battle_intelligence import CaptureDecision, MissionTarget
from app.models.orders import (
    AnnexVassalOrder,
    AnswerCallOrder,
    AnswerDemandOrder,
    AnswerEventOrder,
    AttackOrder,
    CallNegotiationOrder,
    DeclareDefaultOrder,
    DeclareWarOrder,
    DemandFromVassalOrder,
    DenounceAllianceOrder,
    DiplomaticPlayOrder,
    DisbandArmyOrder,
    FabricateClaimOrder,
    GrantConsentOrder,
    HaltArmyOrder,
    HandlePrisonerOrder,
    MapScoutOrder,
    MediateOrder,
    MoveArmyOrder,
    RaiseArmyOrder,
    ReleaseVassalOrder,
    SendEnvoyOrder,
    SetPayOrder,
    SetTaxRateOrder,
    TakeLoanOrder,
)
from app.models.world_battle import StandingPlan
from app.models.world_internal import UprisingResponse
from pydantic import Field, model_validator
from strategy_contracts.ids import FactionId, WholeNumber


class BattleCommandBase(WorldModel):
    faction_id: FactionId
    battle_id: str


class SetPlanCommand(BattleCommandBase):
    kind: Literal["set_plan"] = "set_plan"
    plan: StandingPlan


class CommitReservesCommand(BattleCommandBase):
    kind: Literal["commit_reserves"] = "commit_reserves"


class ReconCommand(BattleCommandBase):
    kind: Literal["reconnoitre"] = "reconnoitre"
    subject_faction_id: FactionId
    target: MissionTarget


class DeceiveCommand(BattleCommandBase):
    kind: Literal["deceive"] = "deceive"


class WithdrawCommand(BattleCommandBase):
    kind: Literal["withdraw"] = "withdraw"


class SurrenderCommand(BattleCommandBase):
    kind: Literal["surrender"] = "surrender"


class CaptureDecisionCommand(BattleCommandBase):
    kind: Literal["capture_decision"] = "capture_decision"
    capture_id: str
    decision: CaptureDecision


class TakeCommandCommand(BattleCommandBase):
    kind: Literal["take_command"] = "take_command"


class DelegateBattleCommand(BattleCommandBase):
    kind: Literal["delegate_battle"] = "delegate_battle"


class ResolveUprisingCommand(WorldModel):
    kind: Literal["resolve_uprising"] = "resolve_uprising"
    faction_id: FactionId
    uprising_id: str
    response: UprisingResponse


BattleCommand = Annotated[
    SetPlanCommand
    | CommitReservesCommand
    | ReconCommand
    | DeceiveCommand
    | WithdrawCommand
    | SurrenderCommand
    | CaptureDecisionCommand,
    Field(discriminator="kind"),
]
Command = Annotated[
    SetPlanCommand
    | CommitReservesCommand
    | ReconCommand
    | DeceiveCommand
    | WithdrawCommand
    | SurrenderCommand
    | CaptureDecisionCommand
    | TakeCommandCommand
    | DelegateBattleCommand
    | ResolveUprisingCommand
    | AnswerEventOrder
    | SetPayOrder
    | TakeLoanOrder
    | DeclareDefaultOrder
    | SetTaxRateOrder
    | RaiseArmyOrder
    | DisbandArmyOrder
    | MoveArmyOrder
    | AttackOrder
    | HaltArmyOrder
    | MapScoutOrder
    | DeclareWarOrder
    | DiplomaticPlayOrder
    | CallNegotiationOrder
    | FabricateClaimOrder
    | SendEnvoyOrder
    | HandlePrisonerOrder
    | MediateOrder
    | AnswerCallOrder
    | DenounceAllianceOrder
    | DemandFromVassalOrder
    | AnswerDemandOrder
    | GrantConsentOrder
    | ReleaseVassalOrder
    | AnnexVassalOrder,
    Field(discriminator="kind"),
]


class CommandStatus(str, Enum):
    ACCEPTED = "accepted"
    DEFERRED = "deferred"
    APPLIED = "applied"
    FAILED = "failed"


class AcceptedCommand(WorldModel):
    id: str
    operation_id: str
    actor_id: str
    faction_id: FactionId
    battle_id: str | None = None
    accepted_turn: WholeNumber
    accepted_wave: int = Field(ge=0, le=4)
    execution_turn: WholeNumber
    execution_wave: int = Field(ge=0, le=4)
    reserved_cost: WholeNumber
    command: Command
    status: CommandStatus = CommandStatus.ACCEPTED
    failure_reason: str | None = None
    applied_turn: WholeNumber | None = None
    applied_wave: int | None = Field(default=None, ge=0, le=4)

    @model_validator(mode="after")
    def validate_command_identity(self) -> "AcceptedCommand":
        if self.command.faction_id != self.faction_id:
            raise ValueError("accepted command faction must match payload")
        payload_battle_id = getattr(self.command, "battle_id", None)
        if payload_battle_id != self.battle_id:
            raise ValueError("accepted command battle must match payload")
        if self.execution_turn < self.accepted_turn:
            raise ValueError("command cannot execute before acceptance")
        if self.battle_id is not None and (self.execution_turn, self.execution_wave) < (
            self.accepted_turn,
            self.accepted_wave,
        ):
            raise ValueError("command cannot execute before acceptance wave")
        if self.status == CommandStatus.FAILED and self.failure_reason is None:
            raise ValueError("failed command requires a reason")
        return self
