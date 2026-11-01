"""Extraction contract (prompt_version extraction_v1), validated plan and step results."""

from typing import Literal

from app.models.common import Assertion, CommitmentKind, CommitmentStatusValue
from pydantic import BaseModel, Field

EXTRACTION_PROMPT_VERSION = "extraction_v1"

ExtractionStepStatus = Literal[
    "idle", "completed", "deadline_reached", "rate_limited", "aborted", "unconfigured"
]


class NewEntity(BaseModel):
    temp_key: str
    entity_type: str
    name: str
    aliases: list[str]
    evidence: list[str]


class ExtractedFact(BaseModel):
    subject: str
    predicate: str
    object: str | None
    object_literal: str | None
    assertion: Assertion
    speaker: str | None
    evidence: list[str]


class SupersessionClaim(BaseModel):
    fact_id: str
    evidence: list[str]
    reason: str


class NewCommitment(BaseModel):
    kind: CommitmentKind
    owner: str
    counterparty: str | None
    summary: str
    evidence: list[str]


class CommitmentUpdate(BaseModel):
    commitment_id: str
    status: CommitmentStatusValue
    evidence: list[str]


class SceneClaim(BaseModel):
    location: str | None
    present: list[str]
    evidence: list[str]


class ExtractionOutput(BaseModel):
    new_entities: list[NewEntity]
    facts: list[ExtractedFact]
    supersessions: list[SupersessionClaim]
    new_commitments: list[NewCommitment]
    commitment_updates: list[CommitmentUpdate]
    scene: SceneClaim | None


class ValidatedPlan(BaseModel):
    """Stored in memory_extraction_batch.validated_plan; apply reads only this."""

    new_entities: list[NewEntity] = Field(default_factory=list)
    reused_entities: dict[str, str] = Field(default_factory=dict)
    facts: list[ExtractedFact] = Field(default_factory=list)
    supersessions: list[SupersessionClaim] = Field(default_factory=list)
    new_commitments: list[NewCommitment] = Field(default_factory=list)
    commitment_updates: list[CommitmentUpdate] = Field(default_factory=list)
    scene: SceneClaim | None = None
    dropped: dict[str, int] = Field(default_factory=dict)


class ExtractionUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0


class ExtractionResult(BaseModel):
    output: ExtractionOutput
    raw_output: dict[str, object]
    usage: ExtractionUsage


class SupersessionJudgement(BaseModel):
    new_fact_index: int
    superseded_fact_id: str | None
    reason: str


class SupersessionJudgeOutput(BaseModel):
    judgements: list[SupersessionJudgement]


class SupersessionJudgeResult(BaseModel):
    output: SupersessionJudgeOutput
    usage: ExtractionUsage


class ExtractionCounts(BaseModel):
    batches_created: int = 0
    batches_applied: int = 0
    batches_failed: int = 0
    items_applied: int = 0
    items_dropped: dict[str, int] = Field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    playthroughs_touched: int = 0
    enrichment_batches: int = 0
