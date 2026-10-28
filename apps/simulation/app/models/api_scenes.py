from uuid import UUID

from app.models.base import WorldModel
from app.models.battle_progress import OperationGuard
from pydantic import Field, model_validator
from strategy_contracts.ids import EntityId, TraitId, WholeNumber
from strategy_contracts.limits import MAX_NAME_CHARS
from strategy_contracts.scene import (
    ParticipantKind,
    SceneInitiator,
    SceneOutcome,
    SceneSituation,
    SceneStatus,
    SceneType,
)
from strategy_contracts.scene_exchange import SceneExchangeView
from strategy_contracts.terms import TermsCard


class SceneStatusResponse(WorldModel):
    scene_id: UUID
    scene_type: SceneType
    status: SceneStatus
    turn: WholeNumber


class OpenNegotiationRequest(OperationGuard):
    counterpart_faction_id: EntityId


class SceneDecisionRequest(OperationGuard):
    is_confirmed: bool
    proposal_sequence: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_sequence_to_confirm(self) -> "SceneDecisionRequest":
        if self.is_confirmed and self.proposal_sequence is None:
            raise ValueError("confirming needs the sequence of the card being signed")
        return self


class SceneParticipantView(WorldModel):
    participant_id: EntityId
    kind: ParticipantKind
    name: str = Field(max_length=MAX_NAME_CHARS)
    trait_ids: list[TraitId] = Field(default_factory=list)


class SceneView(WorldModel):
    scene_id: UUID
    scene_type: SceneType
    status: SceneStatus
    turn: WholeNumber
    initiator: SceneInitiator = SceneInitiator.PLAYER
    is_declinable: bool = True
    situation: SceneSituation
    participants: list[SceneParticipantView] = Field(default_factory=list)
    transcript: list[SceneExchangeView] = Field(default_factory=list)
    exchanges_remaining: WholeNumber
    pending_proposal: TermsCard | None = None
    pending_proposal_sequence: int | None = None
    outcome: SceneOutcome | None = None
