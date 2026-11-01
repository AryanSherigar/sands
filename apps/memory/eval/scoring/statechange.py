"""Scoring for the state-change fixture set. Pure: no database, no model."""

import re
from collections import defaultdict
from dataclasses import dataclass

from app.services.extraction_validator import (
    NEGATION_PREDICATE_TOKENS as NEGATION_TOKENS,
)

from eval.statechange_cases import ForbiddenFact, RequiredFact, StateChangeCase

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
MIN_TOKEN_LENGTH = 3
WORD_COVERAGE_MIN = 0.6
OCCURRED = "occurred"
OVERALL = "overall"


@dataclass(frozen=True)
class ObservedText:
    """`text` is the whole claim: subject name, predicate words and object."""

    subject_key: str | None
    predicate: str
    text: str
    assertion: str


@dataclass(frozen=True)
class CaseOutcome:
    retired_keys: frozenset[str]
    facts: list[ObservedText]
    input_tokens: int = 0
    output_tokens: int = 0
    is_applied: bool = True


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    category: str
    expected_retired: int
    retired_hits: int
    kept_total: int
    wrongly_retired: int
    required_total: int
    required_hits: int
    leaks: int
    negated: int
    input_tokens: int
    output_tokens: int
    is_applied: bool
    observed: tuple[str, ...] = ()


@dataclass(frozen=True)
class Summary:
    cases: int
    unapplied_cases: int
    supersession_recall: float | None
    false_supersession_rate: float | None
    required_recall: float | None
    leaks: int
    negated: int
    input_tokens: int
    output_tokens: int


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in TOKEN_PATTERN.findall(text.lower())
        if len(token) >= MIN_TOKEN_LENGTH
    }


def covers(words: list[str], text: str) -> bool:
    wanted = _tokens(" ".join(words))
    if not wanted:
        return False
    return len(wanted & _tokens(text)) / len(wanted) >= WORD_COVERAGE_MIN


def _has_required(item: RequiredFact, facts: list[ObservedText]) -> bool:
    return any(
        covers(item.words, fact.text)
        and (item.subject is None or fact.subject_key == item.subject)
        for fact in facts
    )


def _is_leaked(item: ForbiddenFact, facts: list[ObservedText]) -> bool:
    return any(
        fact.assertion == OCCURRED and covers(item.words, fact.text) for fact in facts
    )


def _is_negated(fact: ObservedText) -> bool:
    return fact.assertion == OCCURRED and bool(
        NEGATION_TOKENS & set(fact.predicate.split("_"))
    )


def score_case(case: StateChangeCase, outcome: CaseOutcome) -> CaseScore:
    expect = case.expect
    retired = outcome.retired_keys
    return CaseScore(
        case_id=case.case_id,
        category=case.category,
        expected_retired=len(expect.superseded),
        retired_hits=len(set(expect.superseded) & retired),
        kept_total=len(expect.kept),
        wrongly_retired=len(set(expect.kept) & retired),
        required_total=len(expect.required),
        required_hits=sum(
            _has_required(item, outcome.facts) for item in expect.required
        ),
        leaks=sum(_is_leaked(item, outcome.facts) for item in expect.forbidden),
        negated=sum(_is_negated(fact) for fact in outcome.facts),
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        is_applied=outcome.is_applied,
        observed=tuple(f"[{fact.assertion}] {fact.text}" for fact in outcome.facts),
    )


def ratio(hits: int, total: int) -> float | None:
    return hits / total if total else None


def summarize(scores: list[CaseScore]) -> Summary:
    return Summary(
        cases=len(scores),
        unapplied_cases=sum(not score.is_applied for score in scores),
        supersession_recall=ratio(
            sum(s.retired_hits for s in scores), sum(s.expected_retired for s in scores)
        ),
        false_supersession_rate=ratio(
            sum(s.wrongly_retired for s in scores), sum(s.kept_total for s in scores)
        ),
        required_recall=ratio(
            sum(s.required_hits for s in scores), sum(s.required_total for s in scores)
        ),
        leaks=sum(s.leaks for s in scores),
        negated=sum(s.negated for s in scores),
        input_tokens=sum(s.input_tokens for s in scores),
        output_tokens=sum(s.output_tokens for s in scores),
    )


def summarize_by_category(scores: list[CaseScore]) -> dict[str, Summary]:
    grouped: dict[str, list[CaseScore]] = defaultdict(list)
    for score in scores:
        grouped[score.category].append(score)
    result = {name: summarize(items) for name, items in sorted(grouped.items())}
    result[OVERALL] = summarize(scores)
    return result
