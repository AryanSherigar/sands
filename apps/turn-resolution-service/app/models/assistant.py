"""Pydantic v2 schemas for the Studio AI Assistant."""

from typing import Literal

from pydantic import BaseModel, Field


class AssistantChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantStoryCard(BaseModel):
    id: str | None = None
    type: str = "Character"
    name: str = ""
    content: str = ""


class AssistantDraftContext(BaseModel):
    title: str = ""
    logline: str = ""
    genre_tags: list[str] = Field(default_factory=list)
    complexity_tier: str = "newbie"
    player_count_support: str = "solo"
    estimated_playtime: str = ""
    world_lore: str = ""
    opening_prompt: str = ""
    main_conflict: str = ""
    single_lore_prompt: str = ""
    story_cards: list[AssistantStoryCard] = Field(default_factory=list)
    ai_instructions: str = ""
    narrative_style: str = ""
    active_section: str = "meta"


class AssistantEntitySummary(BaseModel):
    entity_id: str
    entity_type: str
    canonical_name: str
    description: str | None = None
    attributes_schema: dict[str, object] = Field(default_factory=dict)


class AssistantFactSummary(BaseModel):
    fact_id: str
    subject_entity_id: str
    predicate: str
    object_entity_id: str | None = None
    object_literal: str | None = None


class AssistantConditionSummary(BaseModel):
    condition_id: str
    label: str


class AssistantInvariantSummary(BaseModel):
    invariant_id: str
    label: str


class AssistantEndConditionSummary(BaseModel):
    end_condition_id: str
    outcome_tag: str
    outcome_title: str


class AssistantMasterContext(BaseModel):
    title: str = ""
    logline: str = ""
    narrator_persona: str = ""
    opening_scene: str = ""
    state_schema: dict[str, object] = Field(default_factory=dict)
    entities: list[AssistantEntitySummary] = Field(default_factory=list)
    facts: list[AssistantFactSummary] = Field(default_factory=list)
    conditions: list[AssistantConditionSummary] = Field(default_factory=list)
    invariants: list[AssistantInvariantSummary] = Field(default_factory=list)
    end_conditions: list[AssistantEndConditionSummary] = Field(default_factory=list)
    active_tab: str = "entities"


class AssistantScopedContext(BaseModel):
    one_line_idea: str = ""
    tab_kind: str = ""
    tab_label: str = ""
    tab_text: str = ""


class AssistantStrategyFaction(BaseModel):
    faction_id: str
    name: str
    leader_id: str | None = None
    leader_name: str = ""
    leader_history: str = ""
    capital_region_id: str | None = None
    treasury: int = 0
    manpower: int = 0
    stability: int = 0
    is_playable: bool = False


class AssistantStrategyRegion(BaseModel):
    region_id: str
    name: str = ""
    owner_id: str | None = None
    population: int = 0
    wealth: int = 0
    manpower: int = 0
    unrest: int = 0
    garrison: int = 0


class AssistantStrategyRelation(BaseModel):
    faction_a: str
    faction_b: str
    status: str


class AssistantStrategyClaim(BaseModel):
    faction_id: str
    region_id: str


class AssistantStrategyGrudge(BaseModel):
    holder_id: str
    target_id: str
    opinion: int = 0
    reason: str = ""


class AssistantStrategyArmy(BaseModel):
    army_id: str
    owner_id: str
    location_id: str
    troops: dict[str, int] = Field(default_factory=dict)
    commander_name: str = ""


class AssistantStrategyTiming(BaseModel):
    start_year: int
    start_month: int
    end_year: int


class AssistantStrategyContext(BaseModel):
    title: str = ""
    timing: AssistantStrategyTiming | None = None
    factions: list[AssistantStrategyFaction] = Field(default_factory=list)
    regions: list[AssistantStrategyRegion] = Field(default_factory=list)
    relations: list[AssistantStrategyRelation] = Field(default_factory=list)
    claims: list[AssistantStrategyClaim] = Field(default_factory=list)
    grudges: list[AssistantStrategyGrudge] = Field(default_factory=list)
    armies: list[AssistantStrategyArmy] = Field(default_factory=list)
    rules: dict[str, object] = Field(default_factory=dict)
    active_panel: str = ""


class AssistantChatRequest(BaseModel):
    messages: list[AssistantChatMessage]
    mode: Literal["newbie", "master", "scoped", "strategy"] = "newbie"
    draft_context: AssistantDraftContext | None = None
    master_context: AssistantMasterContext | None = None
    scoped_context: AssistantScopedContext | None = None
    strategy_context: AssistantStrategyContext | None = None
