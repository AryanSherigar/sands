"""Literal types mirroring every enumerated CHECK constraint in migrations/0001_initial.sql."""

from typing import Literal

ScopeKind = Literal["template", "playthrough"]

TemplateMode = Literal["master", "newbie"]
TemplateDirectStatus = Literal["building", "ready", "failed"]
TemplateEnrichmentStatus = Literal[
    "pending", "running", "ready", "failed", "not_needed"
]

SourceKind = Literal[
    "authored_lore",
    "authored_card",
    "authored_description",
    "authored_fact_text",
    "setup",
    "turn_action",
    "turn_narration",
]
EventKind = Literal[
    "state_mutation",
    "automatic_effect",
    "encounter_outcome",
    "roll",
    "map_discovery",
    "rejected_mutation",
]

EntityProvenance = Literal["authored", "extracted"]
Authority = Literal["authored", "accepted", "extracted"]
Assertion = Literal["occurred", "stated", "attempted", "believed"]

CommitmentKind = Literal["promise", "debt", "quest", "threat"]
CommitmentStatusValue = Literal["open", "fulfilled", "broken", "cancelled"]

EmbeddingTargetKind = Literal["span", "fact"]
ExtractionBatchStatus = Literal["pending", "running", "extracted", "applied", "failed"]
