from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import EntityId, TraitId
from strategy_contracts.limits import MAX_NAME_CHARS, MAX_TEXT_CHARS
from strategy_contracts.negotiation_rules import DEFAULT_MAX_PACT_TURNS
from strategy_contracts.terms import TermKind, TermsCard


class SceneType(str, Enum):
    NEGOTIATION = "negotiation"
    PEACE = "peace"
    BATTLE_SPEECH = "battle_speech"
    REVOLT_TALK = "revolt_talk"
    PROCLAMATION = "proclamation"
    LETTER = "letter"
    HOSTAGE = "hostage"
    JUDGMENT = "judgment"
    EVENT = "event"
    CHRONICLE = "chronicle"
    EPILOGUE = "epilogue"


class SceneStatus(str, Enum):
    PENDING = "pending"
    OPENED = "opened"
    RESOLVED = "resolved"
    DEFAULTED = "defaulted"


class Rubric(str, Enum):
    ADDRESSES_REAL_FEARS = "addresses_real_fears"
    FITS_RULER_CHARACTER = "fits_ruler_character"
    PROMISES_MADE = "promises_made"
    REAL_INTERESTS = "real_interests"
    CREDIBLE_THREATS = "credible_threats"
    VALUED_OFFERS = "valued_offers"
    TONE = "tone"
    JUSTIFICATION = "justification"


MAX_TONE_GRADE = 5


class OutrageLevel(str, Enum):
    NONE = "none"
    ANNOYED = "annoyed"
    OFFENDED = "offended"
    OUTRAGED = "outraged"
    ENRAGED = "enraged"


class ParticipantKind(str, Enum):
    LEADER = "leader"
    COMMANDER = "commander"
    GOVERNOR = "governor"
    OFFICER = "officer"
    ENVOY = "envoy"
    CROWD = "crowd"


class TermsResult(str, Enum):
    AGREED = "agreed"
    WALKED_OUT = "walked_out"
    REFUSED = "refused"


class SubmissionStatus(str, Enum):
    ACCEPTED = "accepted"
    DUPLICATE_IGNORED = "duplicate_ignored"
    REJECTED = "rejected"


class Participant(StrictModel):
    participant_id: EntityId
    kind: ParticipantKind
    name: str = Field(min_length=1, max_length=MAX_NAME_CHARS)
    trait_ids: list[TraitId] = Field(default_factory=list)
    trait_notes: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    mood: str = ""
    memory_notes: list[str] = Field(default_factory=list)


class SituationFact(StrictModel):
    label: str = Field(max_length=MAX_NAME_CHARS)
    value: str = Field(max_length=MAX_TEXT_CHARS)


class SceneSituation(StrictModel):
    summary: str = Field(max_length=MAX_TEXT_CHARS)
    facts: list[SituationFact] = Field(default_factory=list)


class AcceptanceRange(StrictModel):
    accept_at: int
    haggle_at: int

    @model_validator(mode="after")
    def validate_order(self) -> "AcceptanceRange":
        if self.accept_at < self.haggle_at:
            raise ValueError("accept_at must be at least haggle_at")
        return self


class HiddenLimits(StrictModel):
    acceptance: AcceptanceRange | None = None
    real_grievances: list[str] = Field(default_factory=list)
    outrage_level: OutrageLevel = OutrageLevel.NONE
    is_enraged: bool = False


class ChoiceOption(StrictModel):
    id: EntityId
    label: str = Field(max_length=MAX_NAME_CHARS)


class TermsCardSpec(StrictModel):
    kind: Literal["terms_card"] = "terms_card"
    allowed_term_kinds: list[TermKind]
    price_by_term_kind: dict[TermKind, int] = Field(default_factory=dict)
    max_duration_turns: int = Field(default=DEFAULT_MAX_PACT_TURNS, ge=1)
    war_score_available: int = 0


class GradesSpec(StrictModel):
    kind: Literal["grades"] = "grades"
    rubrics: list[Rubric]


class VerdictSpec(StrictModel):
    kind: Literal["verdict"] = "verdict"
    options: list[ChoiceOption]


class ChoiceSpec(StrictModel):
    kind: Literal["choice"] = "choice"
    options: list[ChoiceOption]


class ProseOnlySpec(StrictModel):
    kind: Literal["prose_only"] = "prose_only"


OutcomeSpec = Annotated[
    TermsCardSpec | GradesSpec | VerdictSpec | ChoiceSpec | ProseOnlySpec,
    Field(discriminator="kind"),
]


class RefusedDemand(StrictModel):
    terms_card: TermsCard
    tone_grade: int = Field(default=0, ge=0, le=MAX_TONE_GRADE)


class TermsCardOutcome(StrictModel):
    kind: Literal["terms_card"] = "terms_card"
    result: TermsResult
    terms_card: TermsCard | None = None
    refused_demand: RefusedDemand | None = None


class GradesOutcome(StrictModel):
    kind: Literal["grades"] = "grades"
    grades: dict[Rubric, int]


class VerdictOutcome(StrictModel):
    kind: Literal["verdict"] = "verdict"
    option_id: EntityId


class ChoiceOutcome(StrictModel):
    kind: Literal["choice"] = "choice"
    option_id: EntityId


class ProseOnlyOutcome(StrictModel):
    kind: Literal["prose_only"] = "prose_only"


class SpeechRubric(str, Enum):
    ADDRESSES_FEARS = "addresses_fears"
    FITS_RULER_CHARACTER = "fits_ruler_character"
    PROMISES_MADE = "promises_made"


MAX_SPEECH_RUBRIC_SCORE = 5
MAX_SPEECH_MORALE_SWING = 15


class BattleSpeechOutcome(StrictModel):
    kind: Literal["battle_speech"] = "battle_speech"
    morale_delta_percent: int = Field(
        ge=-MAX_SPEECH_MORALE_SWING, le=MAX_SPEECH_MORALE_SWING
    )
    rubric_scores: dict[SpeechRubric, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scores_are_in_range(self) -> "BattleSpeechOutcome":
        for score in self.rubric_scores.values():
            if not 0 <= score <= MAX_SPEECH_RUBRIC_SCORE:
                raise ValueError(
                    f"rubric scores run from 0 to {MAX_SPEECH_RUBRIC_SCORE}"
                )
        return self


SceneOutcome = Annotated[
    TermsCardOutcome
    | GradesOutcome
    | VerdictOutcome
    | ChoiceOutcome
    | ProseOnlyOutcome,
    Field(discriminator="kind"),
]


class SceneInitiator(str, Enum):
    PLAYER = "player"
    AI = "ai"


class ScenePackage(StrictModel):
    scene_id: UUID
    initiator: SceneInitiator = SceneInitiator.PLAYER
    is_declinable: bool = True
    playthrough_id: UUID
    scene_type: SceneType
    turn: int = Field(ge=0)
    situation: SceneSituation
    participants: list[Participant] = Field(default_factory=list)
    hidden_limits: HiddenLimits | None = None
    allowed_outcomes: list[OutcomeSpec]
    exchange_cap: int = Field(ge=0)
    default_outcome: SceneOutcome


class PublicScenePackage(StrictModel):
    scene_id: UUID
    playthrough_id: UUID
    scene_type: SceneType
    turn: int = Field(ge=0)
    situation: SceneSituation
    participants: list[Participant] = Field(default_factory=list)
    allowed_outcomes: list[OutcomeSpec]
    exchange_cap: int = Field(ge=0)
    default_outcome: SceneOutcome
    initiator: SceneInitiator = SceneInitiator.PLAYER
    is_declinable: bool = True


class ModelAnswerRecord(StrictModel):
    kind: str
    input_hash: str
    answer_json: str
    source: Literal["live", "default"]


class SceneOutcomeSubmission(StrictModel):
    scene_id: UUID
    outcome: SceneOutcome
    model_answers: list[ModelAnswerRecord] = Field(default_factory=list)


class SceneOutcomeResult(StrictModel):
    status: SubmissionStatus
    reason: str | None = None
