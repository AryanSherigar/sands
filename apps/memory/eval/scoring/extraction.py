"""Extraction-layer scoring against plant-derived labels. Pure: no database, no model."""

import re
from dataclasses import dataclass, field

from app.services.extraction_validator import (
    NEGATION_PREDICATE_TOKENS as NEGATION_TOKENS,
)

from eval.labels import ExtractionLabel
from eval.scoring.stats import Interval, bootstrap_interval

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
MIN_TOKEN_LENGTH = 3
OBJECT_OVERLAP_MIN = 0.5
CLAIM_OVERLAP_MIN = 0.5
OCCURRED = "occurred"


@dataclass(frozen=True)
class ObservedFact:
    turns: frozenset[int]
    subject_key: str | None
    predicate: str
    object_key: str | None
    object_text: str
    assertion: str


@dataclass(frozen=True)
class ObservedCommitment:
    turns: frozenset[int]
    owner_key: str | None
    kind: str | None
    status: str
    is_update: bool


@dataclass(frozen=True)
class ObservedEntity:
    name: str
    key: str | None


@dataclass(frozen=True)
class ExtractionObservation:
    facts: list[ObservedFact] = field(default_factory=list)
    commitments: list[ObservedCommitment] = field(default_factory=list)
    supersession_turns: list[frozenset[int]] = field(default_factory=list)
    mentions: list[tuple[frozenset[int], str]] = field(default_factory=list)
    new_entities: list[ObservedEntity] = field(default_factory=list)


@dataclass(frozen=True)
class TypeScore:
    recall: Interval | None
    precision: Interval | None
    recall_hits: int
    label_count: int
    predicted_count: int
    wrong_status: int = 0


@dataclass(frozen=True)
class ExtractionScore:
    by_type: dict[str, TypeScore]
    forbidden_extracted: int
    duplicate_entity_rate: float
    new_entity_count: int
    negated_fact_count: int = 0


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in TOKEN_PATTERN.findall(text.lower())
        if len(token) >= MIN_TOKEN_LENGTH
    }


def _overlap(small: str, large: str) -> float:
    small_tokens = _tokens(small)
    return (
        len(small_tokens & _tokens(large)) / len(small_tokens) if small_tokens else 0.0
    )


def fact_matches(label: ExtractionLabel, fact: ObservedFact) -> bool:
    if label.turn not in fact.turns:
        return False
    if label.subject_key and fact.subject_key != label.subject_key:
        return False
    if label.object_key:
        return fact.object_key == label.object_key
    if label.object_literal:
        return (
            _overlap(label.object_literal, f"{fact.predicate} {fact.object_text}")
            >= OBJECT_OVERLAP_MIN
        )
    claim = f"{fact.predicate.replace('_', ' ')} {fact.object_text}"
    return _overlap(claim, label.anchor_text) >= CLAIM_OVERLAP_MIN


def _forbidden_matches(label: ExtractionLabel, fact: ObservedFact) -> bool:
    is_same_turn = label.turn in fact.turns
    claim = f"{fact.predicate.replace('_', ' ')} {fact.object_text}"
    return (
        fact.assertion == OCCURRED
        and is_same_turn
        and _overlap(claim, label.anchor_text) >= CLAIM_OVERLAP_MIN
    )


def _interval(flags: list[float]) -> Interval | None:
    return bootstrap_interval(flags)


def _score_facts(labels: list[ExtractionLabel], facts: list[ObservedFact]) -> TypeScore:
    recalls = [
        1.0 if any(fact_matches(label, fact) for fact in facts) else 0.0
        for label in labels
    ]
    labeled_turns = {label.turn for label in labels}
    predicted = [fact for fact in facts if fact.turns & labeled_turns]
    precisions = [
        1.0 if any(fact_matches(label, fact) for label in labels) else 0.0
        for fact in predicted
    ]
    return TypeScore(
        _interval(recalls),
        _interval(precisions),
        int(sum(recalls)),
        len(labels),
        len(predicted),
    )


def _commitment_hit(label: ExtractionLabel, item: ObservedCommitment) -> bool:
    if label.turn not in item.turns or item.is_update != bool(
        label.supersedes_label_id
    ):
        return False
    return (
        item.is_update
        or label.subject_key is None
        or item.owner_key == label.subject_key
    )


def _score_commitments(
    labels: list[ExtractionLabel], items: list[ObservedCommitment]
) -> TypeScore:
    matched = [
        next((i for i in items if _commitment_hit(label, i)), None) for label in labels
    ]
    recalls = [0.0 if item is None else 1.0 for item in matched]
    wrong = sum(
        1
        for label, item in zip(labels, matched, strict=True)
        if item is not None and label.status and item.status != label.status
    )
    precisions = [
        1.0 if any(_commitment_hit(label, item) for label in labels) else 0.0
        for item in items
    ]
    return TypeScore(
        _interval(recalls),
        _interval(precisions),
        int(sum(recalls)),
        len(labels),
        len(items),
        wrong,
    )


def _score_supersessions(
    labels: list[ExtractionLabel], turns: list[frozenset[int]]
) -> TypeScore:
    recalls = [
        1.0 if any(label.turn in found for found in turns) else 0.0 for label in labels
    ]
    label_turns = {label.turn for label in labels}
    precisions = [1.0 if found & label_turns else 0.0 for found in turns]
    return TypeScore(
        _interval(recalls),
        _interval(precisions),
        int(sum(recalls)),
        len(labels),
        len(turns),
    )


def _score_links(
    labels: list[ExtractionLabel], mentions: list[tuple[frozenset[int], str]]
) -> TypeScore:
    recalls = [
        1.0
        if any(
            label.turn in turns and key == label.subject_key for turns, key in mentions
        )
        else 0.0
        for label in labels
    ]
    return TypeScore(
        _interval(recalls), None, int(sum(recalls)), len(labels), len(mentions)
    )


def duplicate_entity_rate(
    entities: list[ObservedEntity], authored_keys: set[str]
) -> float:
    seen = set(authored_keys)
    duplicates = 0
    for entity in entities:
        if entity.key is not None and entity.key in seen:
            duplicates += 1
        if entity.key is not None:
            seen.add(entity.key)
    return duplicates / len(entities) if entities else 0.0


def _group_labels(labels: list[ExtractionLabel]) -> dict[str, list[ExtractionLabel]]:
    grouped: dict[str, list[ExtractionLabel]] = {}
    for label in labels:
        grouped.setdefault(label.label_type, []).append(label)
    return grouped


def _forbidden_count(
    forbidden: list[ExtractionLabel], facts: list[ObservedFact]
) -> int:
    return sum(
        1 for label in forbidden for fact in facts if _forbidden_matches(label, fact)
    )


def negated_fact_count(facts: list[ObservedFact]) -> int:
    """Occurred facts whose predicate itself carries the negation (`has_not_paid`)."""
    return sum(
        1
        for fact in facts
        if fact.assertion == OCCURRED
        and NEGATION_TOKENS & set(fact.predicate.lower().split("_"))
    )


def score_extraction(
    labels: list[ExtractionLabel],
    observation: ExtractionObservation,
    authored_keys: set[str],
) -> ExtractionScore:
    grouped = _group_labels(labels)
    by_type = {
        "fact": _score_facts(grouped.get("fact", []), observation.facts),
        "commitment": _score_commitments(
            grouped.get("commitment", []), observation.commitments
        ),
        "supersession": _score_supersessions(
            grouped.get("supersession", []), observation.supersession_turns
        ),
        "entity_link": _score_links(
            grouped.get("entity_link", []), observation.mentions
        ),
    }
    return ExtractionScore(
        by_type=by_type,
        forbidden_extracted=_forbidden_count(
            grouped.get("forbidden_fact", []), observation.facts
        ),
        duplicate_entity_rate=duplicate_entity_rate(
            observation.new_entities, authored_keys
        ),
        new_entity_count=len(observation.new_entities),
        negated_fact_count=negated_fact_count(observation.facts),
    )
