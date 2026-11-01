"""Structured claim matching for state items, whose text is re-rendered rather than verbatim."""

import re
from dataclasses import dataclass

from eval.corpus_models import PlantDef

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
MIN_WORD_LENGTH = 3
OBJECT_OVERLAP_MIN = 0.6


@dataclass(frozen=True)
class Claim:
    subject: str
    predicate: str
    object_text: str


def tokens_of(text: str) -> set[str]:
    return {
        token
        for token in TOKEN_PATTERN.findall(text.lower())
        if len(token) >= MIN_WORD_LENGTH or token.isdigit()
    }


def claim_of(plant: PlantDef, names: dict[str, str]) -> Claim | None:
    if not (plant.subject_key and plant.predicate):
        return None
    object_text = plant.object_literal or names.get(plant.object_key or "", "")
    return Claim(
        names.get(plant.subject_key, plant.subject_key), plant.predicate, object_text
    )


def claim_matches(claim: Claim, text: str) -> bool:
    """Subject words must all be present and the object words mostly present, so a newer
    value of the same attribute is never mistaken for the superseded one."""
    visible = tokens_of(text)
    if not tokens_of(claim.subject) <= visible:
        return False
    wanted = tokens_of(claim.object_text)
    if not wanted:
        return tokens_of(claim.predicate.replace("_", " ")) <= visible
    return len(wanted & visible) / len(wanted) >= OBJECT_OVERLAP_MIN
