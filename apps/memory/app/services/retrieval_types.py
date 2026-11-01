"""Shared in-memory shapes of one retrieval run."""

from dataclasses import dataclass, field
from uuid import UUID

from app.models.common import ScopeKind
from app.models.evidence import SpanRow
from app.models.facts import (
    CommitmentRow,
    CommitmentStatusRow,
    EntityRow,
    FactRow,
    SceneStateRow,
)
from app.models.jobs import EmbeddingModelRow
from app.models.retrieve import RetrievalBranch
from app.services.fusion import Candidate
from app.services.stage_timer import StageTimer

Scope = tuple[ScopeKind, UUID]


def build_scopes(playthrough_id: UUID, template_id: UUID | None) -> list[Scope]:
    """Template scope only when the playthrough has one; never client-chosen."""
    scopes: list[Scope] = []
    if template_id is not None:
        scopes.append(("template", template_id))
    scopes.append(("playthrough", playthrough_id))
    return scopes


@dataclass(frozen=True)
class CommitmentRecord:
    commitment: CommitmentRow
    status: CommitmentStatusRow | None

    @property
    def activity_seq(self) -> int:
        if self.status is None:
            return self.commitment.opened_seq
        return max(self.commitment.opened_seq, self.status.at_seq)

    @property
    def is_open(self) -> bool:
        return self.status is None or self.status.status == "open"


@dataclass
class CandidatePool:
    """Every row a branch returned, so packing never re-reads what a branch fetched.
    Adding a row returns the fusion candidate that identifies it."""

    spans: dict[UUID, SpanRow] = field(default_factory=dict)
    facts: dict[UUID, FactRow] = field(default_factory=dict)
    commitments: dict[UUID, CommitmentRecord] = field(default_factory=dict)

    def add_span(self, span: SpanRow) -> Candidate:
        self.spans[span.span_id] = span
        return Candidate("span", span.span_id, span.sequence)

    def add_fact(self, fact: FactRow) -> Candidate:
        self.facts[fact.fact_id] = fact
        return Candidate("fact", fact.fact_id, fact.valid_from_seq)

    def add_commitment(self, record: CommitmentRecord) -> Candidate:
        commitment_id = record.commitment.commitment_id
        self.commitments[commitment_id] = record
        return Candidate("commitment", commitment_id, record.activity_seq)


@dataclass
class RetrievalRun:
    """Mutable state of one `retrieve` call."""

    pool: CandidatePool = field(default_factory=CandidatePool)
    rankings: dict[RetrievalBranch, list[Candidate]] = field(default_factory=dict)
    skipped: list[RetrievalBranch] = field(default_factory=list)
    seeds: list[EntityRow] = field(default_factory=list)
    scene: SceneStateRow | None = None
    active_model: EmbeddingModelRow | None = None
    timer: StageTimer = field(default_factory=StageTimer)

    @property
    def seed_ids(self) -> list[UUID]:
        return [seed.entity_id for seed in self.seeds]

    @property
    def branch_counts(self) -> dict[str, int]:
        return {branch: len(ranked) for branch, ranked in self.rankings.items()}
