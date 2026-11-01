"""Types and helpers shared by the ingest service modules."""

import hashlib
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.models.common import ScopeKind
from app.models.evidence import SourceRow, SpanCreate, SpanDraft
from psycopg import AsyncConnection

ItemOutcome = Literal["applied", "duplicate"]
OUTCOME_APPLIED: ItemOutcome = "applied"
OUTCOME_DUPLICATE: ItemOutcome = "duplicate"
TEMPLATE_SCOPE: ScopeKind = "template"
PLAYTHROUGH_SCOPE: ScopeKind = "playthrough"


@dataclass(frozen=True)
class TurnContext:
    connection: AsyncConnection
    playthrough_id: UUID
    template_id: UUID | None
    alias_index: dict[str, set[UUID]]


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def memory_scopes(
    playthrough_id: UUID, template_id: UUID | None
) -> list[tuple[ScopeKind, UUID]]:
    scopes: list[tuple[ScopeKind, UUID]] = []
    if template_id is not None:
        scopes.append((TEMPLATE_SCOPE, template_id))
    scopes.append((PLAYTHROUGH_SCOPE, playthrough_id))
    return scopes


def span_from_draft(
    source: SourceRow, draft: SpanDraft, entity_ids: list[UUID]
) -> SpanCreate:
    return SpanCreate(
        source_id=source.source_id,
        scope_kind=source.scope_kind,
        scope_id=source.scope_id,
        sequence=source.sequence,
        ordinal=draft.ordinal,
        start_offset=draft.start_offset,
        end_offset=draft.end_offset,
        text=draft.text,
        token_count=draft.token_count,
        label=draft.label,
        entity_ids=entity_ids,
    )
