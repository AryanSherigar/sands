"""Renders fused candidates into memory items, fits them to the token budget and
groups them for reading. Pure, no I/O."""

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from app.models.common import Assertion, Authority, CommitmentKind, SourceKind
from app.models.evidence import SpanRow
from app.models.facts import FactRow
from app.models.retrieval_rows import SpanOrigin
from app.models.retrieve import MemoryItem, RetrievalBranch
from app.services.fact_text import render_fact_text
from app.services.fusion import FusedCandidate
from app.services.retrieval_types import CandidatePool, CommitmentRecord

COMMITMENT_VERBS: dict[CommitmentKind, str] = {
    "promise": "promised",
    "debt": "owes",
    "quest": "assigned",
    "threat": "threatened",
}
CLAIMED_ASSERTIONS: frozenset[Assertion] = frozenset(
    {"stated", "attempted", "believed"}
)
AUTHORED_SOURCE_KINDS: frozenset[SourceKind] = frozenset(
    {"authored_lore", "authored_card", "authored_description", "authored_fact_text"}
)
GRAPH_AND_EXACT_ONLY_BRANCHES: frozenset[RetrievalBranch] = frozenset(
    {"exact", "graph"}
)
FACT_SOURCE_KIND = "fact"
COMMITMENT_SOURCE_KIND = "commitment"
OPEN_STATUS = "open"
UNKNOWN_ENTITY_NAME = "Someone"


@dataclass(frozen=True)
class RenderContext:
    """`evidence_labels` holds only labels of spans that passed eligibility, keyed by
    span id, so a commitment can never leak a hidden or in-window label."""

    entity_names: Mapping[UUID, str]
    participant_names: Mapping[UUID, str]
    span_origins: Mapping[UUID, SpanOrigin]
    evidence_labels: Mapping[UUID, str]


@dataclass(frozen=True)
class PackBudget:
    budget_tokens: int
    chars_per_token: int
    graph_and_exact_only_share: float
    should_limit_graph_and_exact_only: bool = True


@dataclass(frozen=True)
class PackResult:
    items: list[MemoryItem]
    token_count: int
    is_truncated: bool


def estimate_tokens(text: str, chars_per_token: int) -> int:
    return -(-len(text) // chars_per_token)


def _claimed_by_suffix(assertion: Assertion, speaker: str | None) -> str:
    if assertion in CLAIMED_ASSERTIONS and speaker:
        return f" (claimed by {speaker})"
    return ""


def render_fact(fact: FactRow, context: RenderContext) -> str:
    names = context.entity_names
    object_text = fact.object_literal or ""
    if fact.object_entity_id is not None:
        object_text = names.get(fact.object_entity_id, "")
    body = render_fact_text(
        names.get(fact.subject_entity_id, ""), fact.predicate, object_text
    )
    return body + _claimed_by_suffix(fact.assertion, _fact_speaker(fact, context))


def _fact_speaker(fact: FactRow, context: RenderContext) -> str | None:
    if fact.speaker_entity_id is None:
        return None
    return context.entity_names.get(fact.speaker_entity_id)


def render_commitment(record: CommitmentRecord, context: RenderContext) -> str:
    commitment, status = record.commitment, record.status
    names = context.entity_names
    actors = names.get(commitment.owner_entity_id, UNKNOWN_ENTITY_NAME)
    actors += f" {COMMITMENT_VERBS[commitment.kind]}"
    if commitment.counterparty_entity_id is not None:
        counterparty = names.get(commitment.counterparty_entity_id, UNKNOWN_ENTITY_NAME)
        actors += f" {counterparty}"
    status_name = status.status if status is not None else OPEN_STATUS
    line = (
        f"{actors}: {commitment.summary} — {status_name} (turn {record.activity_seq})"
    )
    return line + _evidence_label_suffix(record, context)


def _evidence_label_suffix(record: CommitmentRecord, context: RenderContext) -> str:
    if record.status is None or record.status.evidence_span_id is None:
        return ""
    label = context.evidence_labels.get(record.status.evidence_span_id)
    return f" [{label}]" if label else ""


def _authority_of_source(source_kind: SourceKind) -> Authority:
    return "authored" if source_kind in AUTHORED_SOURCE_KINDS else "accepted"


def _build_span_item(
    span: SpanRow, branches: list[RetrievalBranch], context: RenderContext
) -> MemoryItem | None:
    origin = context.span_origins.get(span.span_id)
    if origin is None:
        return None
    speaker = None
    if origin.actor_participant_id is not None:
        speaker = context.participant_names.get(origin.actor_participant_id)
    return MemoryItem(
        kind="span",
        item_id=span.span_id,
        source_kind=origin.source_kind,
        authority=_authority_of_source(origin.source_kind),
        assertion=None,
        sequence=span.sequence,
        speaker=speaker,
        text=span.text,
        entity_ids=list(span.entity_ids),
        branches=branches,
    )


def _build_fact_item(
    fact: FactRow, branches: list[RetrievalBranch], context: RenderContext
) -> MemoryItem:
    entity_ids = [fact.subject_entity_id]
    if fact.object_entity_id is not None:
        entity_ids.append(fact.object_entity_id)
    return MemoryItem(
        kind="fact",
        item_id=fact.fact_id,
        source_kind=FACT_SOURCE_KIND,
        authority=fact.authority,
        assertion=fact.assertion,
        sequence=fact.valid_from_seq,
        speaker=_fact_speaker(fact, context),
        text=render_fact(fact, context),
        entity_ids=entity_ids,
        branches=branches,
    )


def _build_commitment_item(
    record: CommitmentRecord, branches: list[RetrievalBranch], context: RenderContext
) -> MemoryItem:
    commitment = record.commitment
    entity_ids = [commitment.owner_entity_id]
    if commitment.counterparty_entity_id is not None:
        entity_ids.append(commitment.counterparty_entity_id)
    return MemoryItem(
        kind="commitment",
        item_id=commitment.commitment_id,
        source_kind=COMMITMENT_SOURCE_KIND,
        authority="extracted",
        assertion=None,
        sequence=record.activity_seq,
        speaker=None,
        text=render_commitment(record, context),
        entity_ids=entity_ids,
        branches=branches,
    )


def build_memory_item(
    fused: FusedCandidate, pool: CandidatePool, context: RenderContext
) -> MemoryItem | None:
    """None when the row is missing from the pool or its origin could not be
    resolved: an item that cannot be rendered faithfully is dropped, not guessed."""
    candidate = fused.candidate
    branches = fused.branches
    if candidate.kind == "span" and candidate.item_id in pool.spans:
        return _build_span_item(pool.spans[candidate.item_id], branches, context)
    if candidate.kind == "fact" and candidate.item_id in pool.facts:
        return _build_fact_item(pool.facts[candidate.item_id], branches, context)
    if candidate.kind == "commitment" and candidate.item_id in pool.commitments:
        record = pool.commitments[candidate.item_id]
        return _build_commitment_item(record, branches, context)
    return None


def build_ranked_items(
    fused_candidates: list[FusedCandidate],
    pool: CandidatePool,
    context: RenderContext,
) -> list[MemoryItem]:
    items = [build_memory_item(fused, pool, context) for fused in fused_candidates]
    return [item for item in items if item is not None]


def _is_graph_or_exact_only(item: MemoryItem) -> bool:
    return set(item.branches) <= GRAPH_AND_EXACT_ONLY_BRANCHES


class _BudgetTracker:
    def __init__(self, budget: PackBudget) -> None:
        self._budget = budget
        self.used_tokens = 0
        self._restricted_tokens = 0

    def try_take(self, item: MemoryItem) -> bool:
        budget = self._budget
        cost = estimate_tokens(item.text, budget.chars_per_token)
        if self.used_tokens + cost > budget.budget_tokens:
            return False
        is_restricted = (
            budget.should_limit_graph_and_exact_only and _is_graph_or_exact_only(item)
        )
        share_cap = budget.graph_and_exact_only_share * budget.budget_tokens
        if is_restricted and self._restricted_tokens + cost > share_cap:
            return False
        self.used_tokens += cost
        if is_restricted:
            self._restricted_tokens += cost
        return True


def _select_within_budget(
    ranked_items: list[MemoryItem], budget: PackBudget
) -> tuple[list[MemoryItem], int, bool]:
    tracker = _BudgetTracker(budget)
    selected: list[MemoryItem] = []
    is_truncated = False
    for item in ranked_items:
        if tracker.try_take(item):
            selected.append(item)
        else:
            is_truncated = True
    return selected, tracker.used_tokens, is_truncated


def _primary_entity_id(item: MemoryItem, seed_entity_ids: set[UUID]) -> UUID | None:
    for entity_id in item.entity_ids:
        if entity_id in seed_entity_ids:
            return entity_id
    return item.entity_ids[0] if item.entity_ids else None


def _group_by_primary_entity(
    selected: list[MemoryItem], seed_entity_ids: set[UUID]
) -> list[MemoryItem]:
    groups: dict[UUID | None, list[MemoryItem]] = {}
    for item in selected:
        groups.setdefault(_primary_entity_id(item, seed_entity_ids), []).append(item)
    ordered_keys = [key for key in groups if key is not None]
    if None in groups:
        ordered_keys.append(None)
    grouped: list[MemoryItem] = []
    for key in ordered_keys:
        grouped.extend(sorted(groups[key], key=_chronological_key))
    return grouped


def _chronological_key(item: MemoryItem) -> tuple[int, str]:
    return (item.sequence, str(item.item_id))


def pack_items(
    ranked_items: list[MemoryItem], seed_entity_ids: list[UUID], budget: PackBudget
) -> PackResult:
    """`ranked_items` is in fused order. Items are taken whole: one that does not fit
    the remaining budget is skipped and the next is tried, so the output never
    exceeds the budget and never holds a partial clause. Output is grouped by primary
    entity (groups by best fused rank, no-entity items last), oldest first within
    a group."""
    selected, used_tokens, is_truncated = _select_within_budget(ranked_items, budget)
    grouped = _group_by_primary_entity(selected, set(seed_entity_ids))
    return PackResult(grouped, used_tokens, is_truncated)
