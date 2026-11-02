from enum import Enum

from pydantic import Field

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import EntityId, FactionId, WholeNumber
from strategy_contracts.limits import (
    MAX_CITED_GRUDGES,
    MAX_TERMS_PER_CARD,
    MAX_TEXT_CHARS,
)
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scene import (
    MAX_TONE_GRADE,
    ScenePackage,
    SceneStatus,
    SubmissionStatus,
)
from strategy_contracts.terms import PromiseKind, Term, TermsCard
from strategy_contracts.treaty import Verdict, WeightBand


class SceneAction(str, Enum):
    CONTINUE_TALK = "continue_talk"
    PROPOSE_TERMS = "propose_terms"
    WALK_OUT = "walk_out"
    REFUSE = "refuse"
    CHOOSE_OPTION = "choose_option"


class SceneDecision(StrictModel):
    action: SceneAction
    duration_turns: int | None = Field(default=None, ge=1)
    option_id: EntityId | None = None
    nuance_id: EntityId | None = None
    peace_tier: PeaceTier | None = None
    is_white_peace: bool = False
    guarantor_ids: list[FactionId] = Field(default_factory=list)
    terms: list[Term] = Field(default_factory=list, max_length=MAX_TERMS_PER_CARD)
    cited_grudge_ids: list[EntityId] = Field(
        default_factory=list, max_length=MAX_CITED_GRUDGES
    )
    promise_kind: PromiseKind | None = None
    promise_subject_id: EntityId | None = None
    is_promise_by_ruler: bool = False
    tone_grade: int = Field(default=2, ge=0, le=MAX_TONE_GRADE)


class SceneExchangeSubmission(StrictModel):
    sequence: int = Field(ge=1)
    player_text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    leader_text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    decision: SceneDecision
    tone_grade: int = Field(default=0, ge=0, le=MAX_TONE_GRADE)


class LetterBodySubmission(StrictModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)


class SceneExchangeResult(StrictModel):
    status: SubmissionStatus
    scene_status: SceneStatus
    exchanges_remaining: WholeNumber
    pending_proposal: TermsCard | None = None
    reason: str | None = None
    verdict: Verdict | None = None
    clause_bands: list[WeightBand] = Field(default_factory=list)


class SceneExchangeView(StrictModel):
    sequence: int
    player_text: str
    leader_text: str
    proposal: TermsCard | None = None
    verdict: Verdict | None = None
    clause_bands: list[WeightBand] = Field(default_factory=list)


class InternalScenePackage(StrictModel):
    package: ScenePackage
    status: SceneStatus
    transcript: list[SceneExchangeView] = Field(default_factory=list)
    exchanges_remaining: WholeNumber


class SceneFailureResult(StrictModel):
    scene_status: SceneStatus
    failed_attempts: WholeNumber
    attempts_remaining: WholeNumber
