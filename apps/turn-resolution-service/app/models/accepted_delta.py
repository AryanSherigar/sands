"""What a turn accepted, as stored on TurnLog.accepted_delta and sent to memory.

The shape is owned by docs/memory-specs/memory-turn-ingestion.spec.md §3.4 and
must stay compatible with apps/memory's AcceptedDelta.
"""

from typing import Literal

from pydantic import BaseModel, Field

AcceptedDeltaKind = Literal[
    "state_mutation",
    "automatic_effect",
    "encounter_outcome",
    "roll",
    "map_discovery",
]


class AcceptedDeltaItem(BaseModel):
    """One accepted change; key is stable per item within a turn."""

    kind: AcceptedDeltaKind
    key: str
    before: object | None = None
    after: object | None = None
    detail: dict[str, object] = Field(default_factory=dict)


class AcceptedDelta(BaseModel):
    """All accepted changes of one turn."""

    items: list[AcceptedDeltaItem] = Field(default_factory=list)
