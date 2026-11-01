"""Blind grading support for the generation layer: batches, audit samples, agreement."""

import random
from collections import Counter
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel

from eval.corpus_models import ProbeDef
from eval.heldout import tokens_of

Grade = Literal["correct", "incorrect", "not_addressed"]
Arm = Literal["baseline", "tuned"]
GRADES: tuple[Grade, ...] = ("correct", "incorrect", "not_addressed")
SHUFFLE_SEED = 20261026
CALIBRATION_ITEMS = 40
STRATIFIED_ITEMS = 50
MIN_RAW_AGREEMENT = 0.85
MIN_KAPPA = 0.6


class Narration(BaseModel):
    probe_id: str
    arm: Arm
    sample: int
    text: str


class BlindItem(BaseModel):
    item_id: str
    probe_id: str
    action_text: str
    expected_truth: str
    required_evidence: list[str]
    forbidden_evidence: list[str]
    narration: str


class AnchorSignals(BaseModel):
    required_found: int
    required_total: int
    has_forbidden: bool


def _contains(text: str, anchor: str) -> bool:
    return " ".join(tokens_of(anchor)) in " ".join(tokens_of(text))


def anchor_signals(
    narration: str, required_anchors: list[str], probe: ProbeDef
) -> AnchorSignals:
    return AnchorSignals(
        required_found=sum(
            1 for anchor in required_anchors if _contains(narration, anchor)
        ),
        required_total=len(required_anchors),
        has_forbidden=any(_contains(narration, a) for a in probe.forbidden_anchors),
    )


def blind_batches(
    narrations: list[Narration],
    probes: dict[str, ProbeDef],
    required_texts: dict[str, list[str]],
    batch_size: int,
) -> tuple[list[list[BlindItem]], dict[str, Narration]]:
    """Returns shuffled batches that never name the arm, plus the key that maps item ids back."""
    order = list(range(len(narrations)))
    random.Random(SHUFFLE_SEED).shuffle(order)
    key: dict[str, Narration] = {}
    items: list[BlindItem] = []
    for position, index in enumerate(order):
        narration = narrations[index]
        probe = probes[narration.probe_id]
        item_id = f"i{position:04d}"
        key[item_id] = narration
        items.append(
            BlindItem(
                item_id=item_id,
                probe_id=probe.probe_id,
                action_text=probe.action_text,
                expected_truth=probe.expected_truth,
                required_evidence=required_texts.get(probe.probe_id, []),
                forbidden_evidence=probe.forbidden_anchors,
                narration=narration.text,
            )
        )
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)], key


def raw_agreement(pairs: Sequence[tuple[Grade, Grade]]) -> float:
    return sum(1 for first, second in pairs if first == second) / len(pairs)


def cohens_kappa(pairs: Sequence[tuple[Grade, Grade]]) -> float:
    total = len(pairs)
    observed = raw_agreement(pairs)
    first = Counter(a for a, _ in pairs)
    second = Counter(b for _, b in pairs)
    expected = sum(first[g] * second[g] for g in GRADES) / (total * total)
    return 1.0 if expected == 1.0 else (observed - expected) / (1.0 - expected)


def agreement_is_sufficient(pairs: Sequence[tuple[Grade, Grade]]) -> bool:
    return (
        raw_agreement(pairs) >= MIN_RAW_AGREEMENT and cohens_kappa(pairs) >= MIN_KAPPA
    )


def audit_sample(
    class_by_item: dict[str, str],
    calibration: int = CALIBRATION_ITEMS,
    stratified: int = STRATIFIED_ITEMS,
) -> tuple[list[str], list[str]]:
    """A calibration set of random items, then a class-balanced set of further items."""
    rng = random.Random(SHUFFLE_SEED)
    ids = sorted(class_by_item)
    rng.shuffle(ids)
    first, rest = ids[:calibration], ids[calibration:]
    by_class: dict[str, list[str]] = {}
    for item_id in rest:
        by_class.setdefault(class_by_item[item_id], []).append(item_id)
    chosen: list[str] = []
    while len(chosen) < stratified and any(by_class.values()):
        for name in sorted(by_class):
            if by_class[name] and len(chosen) < stratified:
                chosen.append(by_class[name].pop())
    return first, chosen
