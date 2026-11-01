"""Shared shapes and flag drawing for the retrieval latency corpora."""

import random
from dataclasses import dataclass, field
from uuid import UUID

from app.models.common import TemplateMode

HIDDEN_OR_CONDITIONAL_SPLIT = 2
UNREVEALABLE_SHARE = 0.5


@dataclass(frozen=True)
class CorpusSpec:
    name: str
    mode: TemplateMode
    entity_count: int
    relation_fact_count: int
    attribute_fact_count: int
    hub_count: int
    turn_count: int
    hidden_fraction: float
    commitment_count: int
    scene_every_turns: int
    target_embeddable: int | None
    fixed_lore_count: int


@dataclass
class BuiltCorpus:
    spec: CorpusSpec
    template_id: UUID
    playthrough_id: UUID
    turn_count: int = 0
    revealable_ids: list[UUID] = field(default_factory=list)
    conditional_ids: list[UUID] = field(default_factory=list)


@dataclass(frozen=True)
class Flags:
    is_hidden: bool
    conditional: bool
    authored_fact_id: UUID | None


def make_uuid(rng: random.Random) -> UUID:
    return UUID(int=rng.getrandbits(128), version=4)


def draw_flags(rng: random.Random, corpus: BuiltCorpus) -> Flags:
    """Half of the flagged items keep no authored id, so no request can reveal or
    activate them and eligibility has to reject them."""
    roll = rng.random()
    fraction = corpus.spec.hidden_fraction
    authored_id = make_uuid(rng)
    is_hidden = roll < fraction / HIDDEN_OR_CONDITIONAL_SPLIT
    is_conditional = not is_hidden and roll < fraction
    is_flagged = is_hidden or is_conditional
    if is_flagged and rng.random() < UNREVEALABLE_SHARE:
        return Flags(is_hidden, is_conditional, None)
    if is_hidden:
        corpus.revealable_ids.append(authored_id)
    if is_conditional:
        corpus.conditional_ids.append(authored_id)
    return Flags(is_hidden, is_conditional, authored_id)


class MeasurementError(RuntimeError):
    """The measurement cannot be trusted; the script aborts instead of reporting."""
