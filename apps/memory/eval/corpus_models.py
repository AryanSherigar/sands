"""File formats of an evaluation campaign. Every reference between files is a string key."""

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

FailureClass = Literal[
    "long_range",
    "knowledge_update",
    "commitment_status",
    "multi_hop",
    "attribution",
    "negation_conditional",
    "rejected_mutation",
    "hidden_reveal",
    "conditional_fact",
    "isolation",
    "lore_scale",
    "pronoun_reference",
    "injection",
]
UNMEASURED_CLASSES: frozenset[str] = frozenset({"lore_scale", "attribution"})
MEASURED_CLASSES: tuple[str, ...] = tuple(
    name for name in get_args(FailureClass) if name not in UNMEASURED_CLASSES
)
MIN_PROBES_PER_CLASS = 8

ProbeStyle = Literal["direct", "vague"]
CampaignMode = Literal["master", "newbie"]
ActionMode = Literal["say", "do", "story", "see"]
PlantKind = Literal[
    "fact",
    "commitment",
    "supersession",
    "entity_link",
    "relation",
    "rejected",
    "negated",
]
PlantSource = Literal["turn", "card", "lore", "authored_fact", "delta"]
CommitmentStatus = Literal["open", "fulfilled", "broken", "cancelled"]
CommitmentKindName = Literal["promise", "debt", "quest", "threat"]


class CorpusModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EntityDef(CorpusModel):
    key: str
    entity_type: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    is_player: bool = False


class AuthoredFactDef(CorpusModel):
    key: str
    subject_key: str
    predicate: str
    object_key: str | None = None
    object_literal: str | None = None
    is_hidden: bool = False
    when_active: dict[str, object] | None = None
    superseded_fact_key: str | None = None


class CardDef(CorpusModel):
    card_id: str
    type: str
    name: str
    content: str


class ParticipantDef(CorpusModel):
    key: str
    display_name: str


class ScenarioFile(CorpusModel):
    campaign_id: str
    mode: CampaignMode
    title: str
    player_entity_key: str | None = None
    participants: list[ParticipantDef]
    entities: list[EntityDef] = Field(default_factory=list)
    facts: list[AuthoredFactDef] = Field(default_factory=list)
    cards: list[CardDef] = Field(default_factory=list)
    world_lore: str = ""
    single_lore_prompt: str = ""
    main_conflict: str = ""
    opening_prompt: str = ""
    tracked_fields: list[str] = Field(default_factory=list)


class DeltaDef(CorpusModel):
    kind: Literal["state_mutation", "automatic_effect", "roll", "map_discovery"]
    entity_key: str
    attribute: str
    before: object | None = None
    after: object | None = None


class RejectedCallDef(CorpusModel):
    tool_name: str
    arguments: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] = Field(default_factory=dict)


class SnapshotDef(CorpusModel):
    scene_entity_keys: list[str] = Field(default_factory=list)
    revealed_fact_keys: list[str] = Field(default_factory=list)
    active_conditional_fact_keys: list[str] = Field(default_factory=list)
    interlocutor_key: str | None = None


class TurnDef(CorpusModel):
    turn_number: int = Field(ge=1)
    participant_key: str
    action_mode: ActionMode
    action_text: str
    narration_text: str
    delta: list[DeltaDef] = Field(default_factory=list)
    rejected_calls: list[RejectedCallDef] = Field(default_factory=list)
    snapshot: SnapshotDef = Field(default_factory=SnapshotDef)


class PlantDef(CorpusModel):
    plant_id: str
    source: PlantSource
    turn: int = Field(ge=0)
    source_ref: str | None = None
    kind: PlantKind
    anchor_text: str = Field(min_length=3)
    subject_key: str | None = None
    predicate: str | None = None
    object_key: str | None = None
    object_literal: str | None = None
    commitment_kind: CommitmentKindName | None = None
    status: CommitmentStatus | None = None
    supersedes_plant_id: str | None = None
    fact_key: str | None = None


class ProbeDef(CorpusModel):
    probe_id: str
    failure_class: FailureClass
    at_turn: int = Field(ge=1)
    action_text: str
    action_mode: ActionMode
    actor_key: str
    required: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    forbidden_anchors: list[str] = Field(default_factory=list)
    distractors: list[str] = Field(default_factory=list)
    style: ProbeStyle = "direct"
    expected_truth: str
