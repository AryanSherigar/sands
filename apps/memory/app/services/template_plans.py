"""Value objects the template builders hand to the template service. No I/O."""

from dataclasses import dataclass, field
from uuid import UUID

from app.models.common import SourceKind
from app.models.evidence import SpanDraft
from app.models.facts import FactCreate


@dataclass(frozen=True)
class SpanLimits:
    max_tokens: int
    chars_per_token: int


@dataclass(frozen=True)
class SpanPlan:
    draft: SpanDraft
    entity_ids: list[UUID] = field(default_factory=list)
    is_hidden: bool = False
    conditional: bool = False
    authored_fact_id: UUID | None = None


@dataclass(frozen=True)
class SourcePlan:
    source_kind: SourceKind
    source_ref: str
    content: str
    spans: list[SpanPlan]


@dataclass(frozen=True)
class FactPlan:
    fact: FactCreate
    source: SourcePlan
