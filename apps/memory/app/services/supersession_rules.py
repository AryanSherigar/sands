"""Pure rules for deciding which live facts a new fact replaces. No I/O."""

import re
from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from app.models.extraction import (
    ExtractedFact,
    SupersessionClaim,
    SupersessionJudgement,
    SupersessionJudgeOutput,
)
from app.models.facts import FactRow
from app.services.fact_text import render_fact_text

WORD_PATTERN = re.compile(r"[a-z0-9]+")
MIN_OVERLAP_WORD_LENGTH = 3
SMALL_SUBJECT_FACT_COUNT = 8
STOP_WORDS = frozenset(
    [
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "into",
        "her",
        "his",
        "its",
        "was",
        "were",
        "are",
        "has",
        "had",
        "not",
        "but",
        "all",
        "one",
        "two",
        "out",
        "now",
        "new",
        "old",
        "who",
        "she",
        "him",
        "they",
        "them",
        "their",
        "there",
        "then",
        "than",
    ]
)
EVIDENCE_PREVIEW_CHARS = 240
OCCURRED = "occurred"
ACCEPTED_AUTHORITY = "accepted"
REASON_FUNCTIONAL = "functional_predicate_changed"
DROP_JUDGE_BAD_INDEX = "judge_bad_index"
DROP_JUDGE_UNOFFERED_ID = "judge_unoffered_id"


@dataclass(frozen=True)
class FactCandidates:
    fact_index: int
    fact: ExtractedFact
    subject_id: UUID
    candidates: tuple[FactRow, ...]


@dataclass(frozen=True)
class CandidateContext:
    """What selection needs beyond the new fact: id references, entity names, the live
    facts of every entity in play, and how many live facts each subject has."""

    refs: dict[str, str]
    names: dict[str, str]
    live_rows: tuple[FactRow, ...]
    cap: int


def _words(text: str | None) -> list[str]:
    return WORD_PATTERN.findall((text or "").lower())


def _significant(text: str | None) -> set[str]:
    return {
        word
        for word in _words(text)
        if len(word) >= MIN_OVERLAP_WORD_LENGTH and word not in STOP_WORDS
    }


def object_key(fact: ExtractedFact, refs: dict[str, str]) -> str | None:
    if fact.object is None:
        return None
    return refs.get(fact.object, fact.object)


def _is_same_value(fact: ExtractedFact, row: FactRow, refs: dict[str, str]) -> bool:
    row_object = str(row.object_entity_id) if row.object_entity_id else None
    return (
        fact.predicate == row.predicate
        and object_key(fact, refs) == row_object
        and _words(fact.object_literal) == _words(row.object_literal)
    )


def _name_words(key: str | None, ctx: CandidateContext) -> set[str]:
    if key is None:
        return set()
    return _significant(ctx.names.get(ctx.refs.get(key, key)))


def _claim_words(fact: ExtractedFact, ctx: CandidateContext) -> set[str]:
    return (
        _significant(fact.object_literal)
        | _name_words(fact.subject, ctx)
        | _name_words(fact.object, ctx)
    )


def _row_words(row: FactRow, ctx: CandidateContext) -> set[str]:
    object_name = ctx.names.get(str(row.object_entity_id), "")
    return _significant(row.object_literal) | _significant(object_name)


def _subject_counts(rows: tuple[FactRow, ...]) -> Counter[UUID]:
    return Counter(row.subject_entity_id for row in rows)


def select_candidates(
    fact: ExtractedFact, subject_id: UUID, ctx: CandidateContext
) -> tuple[FactRow, ...]:
    """Live facts the new one may replace: same subject and predicate; any fact whose
    object shares a word with the new claim (a holder or place change moves the
    subject); and every fact of a subject that has only a few. Best matches first."""
    counts = _subject_counts(ctx.live_rows)
    claim = _claim_words(fact, ctx)
    scored: list[tuple[tuple[bool, int, int], FactRow]] = []
    for row in ctx.live_rows:
        if row.assertion != OCCURRED or row.authority == ACCEPTED_AUTHORITY:
            continue
        if _is_same_value(fact, row, ctx.refs):
            continue
        is_same_subject = row.subject_entity_id == subject_id
        is_same_slot = is_same_subject and row.predicate == fact.predicate
        overlap = len(claim & _row_words(row, ctx))
        is_small = is_same_subject and counts[subject_id] <= SMALL_SUBJECT_FACT_COUNT
        if is_same_slot or overlap or is_small:
            scored.append(((is_same_slot, overlap, row.valid_from_seq), row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return tuple(row for _, row in scored[: ctx.cap])


def _claim(row: FactRow, fact: ExtractedFact, reason: str) -> SupersessionClaim:
    return SupersessionClaim(
        fact_id=str(row.fact_id), evidence=list(fact.evidence), reason=reason
    )


def split_by_tier(
    pairs: list[FactCandidates], functional_predicates: frozenset[str]
) -> tuple[list[SupersessionClaim], list[FactCandidates]]:
    """A functional predicate holds one value, so a changed value replaces every
    live fact with that subject and predicate; the rest need the judge."""
    claims: list[SupersessionClaim] = []
    ambiguous: list[FactCandidates] = []
    for pair in pairs:
        is_functional = pair.fact.predicate in functional_predicates
        replaced = [
            row
            for row in pair.candidates
            if is_functional
            and row.predicate == pair.fact.predicate
            and row.subject_entity_id == pair.subject_id
        ]
        claims.extend(_claim(row, pair.fact, REASON_FUNCTIONAL) for row in replaced)
        left = tuple(row for row in pair.candidates if row not in replaced)
        if left:
            ambiguous.append(
                FactCandidates(pair.fact_index, pair.fact, pair.subject_id, left)
            )
    return claims, ambiguous


def _object_text(
    entity_key: str | None, literal: str | None, names: dict[str, str]
) -> str:
    if entity_key is not None:
        return names.get(entity_key, "")
    return (literal or "").strip()


def render_candidate_line(row: FactRow, names: dict[str, str]) -> str:
    row_object = str(row.object_entity_id) if row.object_entity_id else None
    text = render_fact_text(
        names.get(str(row.subject_entity_id), ""),
        row.predicate,
        _object_text(row_object, row.object_literal, names),
    )
    return f"  [{row.fact_id}] {text}"


def render_new_fact_line(
    pair: FactCandidates,
    refs: dict[str, str],
    names: dict[str, str],
    evidence_text: str,
) -> str:
    fact = pair.fact
    text = render_fact_text(
        names.get(str(pair.subject_id), ""),
        fact.predicate,
        _object_text(object_key(fact, refs), fact.object_literal, names),
    )
    preview = evidence_text[:EVIDENCE_PREVIEW_CHARS]
    return f"[N{pair.fact_index}] {text}\n  evidence: {preview}"


def render_judge_input(
    pairs: list[FactCandidates],
    refs: dict[str, str],
    names: dict[str, str],
    evidence_by_index: dict[int, str],
) -> str:
    blocks = []
    for pair in pairs:
        head = render_new_fact_line(
            pair, refs, names, evidence_by_index.get(pair.fact_index, "")
        )
        lines = [render_candidate_line(row, names) for row in pair.candidates]
        blocks.append("\n".join([head, "  OLD FACTS:", *lines]))
    return "\n\n".join(blocks)


def _judged_claim(
    judgement: SupersessionJudgement,
    by_index: dict[int, FactCandidates],
    drops: Counter[str],
) -> SupersessionClaim | None:
    pair = by_index.get(judgement.new_fact_index)
    if pair is None:
        drops[DROP_JUDGE_BAD_INDEX] += 1
        return None
    if judgement.superseded_fact_id is None:
        return None
    offered = {str(row.fact_id): row for row in pair.candidates}
    row = offered.get(judgement.superseded_fact_id)
    if row is None:
        drops[DROP_JUDGE_UNOFFERED_ID] += 1
        return None
    return _claim(row, pair.fact, judgement.reason.strip())


def validate_judgements(
    output: SupersessionJudgeOutput, pairs: list[FactCandidates]
) -> tuple[list[SupersessionClaim], Counter[str]]:
    """A judgement may only name a fact id that was offered for that new fact."""
    by_index = {pair.fact_index: pair for pair in pairs}
    drops: Counter[str] = Counter()
    judged = (_judged_claim(item, by_index, drops) for item in output.judgements)
    return merge_claims([], [claim for claim in judged if claim is not None]), drops


def merge_claims(
    existing: list[SupersessionClaim], added: list[SupersessionClaim]
) -> list[SupersessionClaim]:
    """Model-cited claims stay first; a fact id appears at most once."""
    merged: dict[str, SupersessionClaim] = {}
    for claim in [*existing, *added]:
        merged.setdefault(claim.fact_id, claim)
    return list(merged.values())
