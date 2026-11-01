"""Checks authored state-change cases and merges the part files into cases.jsonl.

`python -m eval.statechange_check` prints every problem and writes nothing;
`python -m eval.statechange_check --write` merges only when there are none."""

import re
import sys
from pathlib import Path

from eval.scoring.statechange import covers
from eval.statechange_cases import CASES_FILE, StateChangeCase, load_cases
from eval.statechange_seed import PLAYER_NAME

PARTS_DIRECTORY = CASES_FILE.parent / "parts"
META_PATTERN = re.compile(
    r"supersede|replaces|no longer true|stale|old fact|prior fact", re.IGNORECASE
)
EXPECTED_COUNTS = {
    "change": 12,
    "outside_context": 5,
    "additive": 8,
    "negation": 6,
    "rejected": 5,
}
MIN_FILLER_COUNT = 150


def _narration(case: StateChangeCase) -> str:
    turns = " ".join(f"{turn.action} {turn.narration}" for turn in case.turns)
    return f"{turns} {PLAYER_NAME}"


def _meta_problems(case: StateChangeCase) -> list[str]:
    text = f"{_narration(case)} {case.note}"
    return [f"{case.case_id}: meta language {m!r}" for m in META_PATTERN.findall(text)]


def _required_problems(case: StateChangeCase) -> list[str]:
    narration = _narration(case)
    return [
        f"{case.case_id}: required words {item.words} not found in the turns"
        for item in case.expect.required
        if not covers(item.words, narration)
    ]


def _coverage_problems(case: StateChangeCase) -> list[str]:
    listed = set(case.expect.superseded) | set(case.expect.kept)
    unlisted = {fact.key for fact in case.prior_facts} - listed
    return [
        f"{case.case_id}: prior fact {key} is in neither list"
        for key in sorted(unlisted)
    ]


def _category_problems(case: StateChangeCase) -> list[str]:
    problems: list[str] = []
    if case.category == "change" and not case.expect.superseded:
        problems.append(f"{case.case_id}: a change case retires nothing")
    retires = case.category in ("change", "outside_context")
    if case.expect.superseded and not retires:
        problems.append(f"{case.case_id}: only change cases may retire facts")
    if case.category == "outside_context" and case.filler_count < MIN_FILLER_COUNT:
        problems.append(f"{case.case_id}: filler_count under {MIN_FILLER_COUNT}")
    if case.category == "rejected" and not any(t.rejected for t in case.turns):
        problems.append(f"{case.case_id}: a rejected case has no rejected change")
    if case.category in ("negation", "rejected") and not case.expect.forbidden:
        problems.append(f"{case.case_id}: no forbidden proposition")
    return problems


def check_case(case: StateChangeCase) -> list[str]:
    return [
        *_meta_problems(case),
        *_required_problems(case),
        *_coverage_problems(case),
        *_category_problems(case),
    ]


def _count_problems(cases: list[StateChangeCase]) -> list[str]:
    counts = {name: 0 for name in EXPECTED_COUNTS}
    for case in cases:
        counts[case.category] += 1
    return [
        f"category {name}: {counts[name]} cases, expected {expected}"
        for name, expected in EXPECTED_COUNTS.items()
        if counts[name] != expected
    ]


def load_parts() -> list[StateChangeCase]:
    cases: list[StateChangeCase] = []
    for path in sorted(PARTS_DIRECTORY.glob("*.jsonl")):
        cases.extend(load_cases(path))
    return cases


def main(should_write: bool) -> int:
    cases = load_parts()
    problems = [issue for case in cases for issue in check_case(case)]
    problems += _count_problems(cases)
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        problems.append("duplicate case ids across part files")
    for problem in problems:
        print(problem)
    if problems or not should_write:
        print(f"{len(cases)} cases, {len(problems)} problems")
        return 1 if problems else 0
    lines = [case.model_dump_json() for case in cases]
    Path(CASES_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases to {CASES_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main("--write" in sys.argv))
