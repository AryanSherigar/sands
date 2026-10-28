import type { ComplexityTier } from "@/shared/constants/complexity-tiers";
import type {
  ScenarioMode,
  ScenarioVisibility,
} from "@/shared/types/scenarioSummary.types";
import { SetupInputField } from "../stores/studio.store";
import type { LoreDocument } from "./lore.types";

export type StateFieldType =
  | "string"
  | "number"
  | "boolean"
  | "enum"
  | "entity_ref"
  | "list"
  | "object"
  | "derived";

export type StateFieldOption = string | { value: string; label?: string };

export interface StateFieldDefinition {
  type: StateFieldType;
  label?: string;
  description?: string;
  initial?: unknown;
  min?: number;
  max?: number;
  entity_type?: string;
  fields?: Record<string, StateFieldDefinition>;
  item_type?: StateFieldType;
  formula?: string;
  options?: StateFieldOption[];
  hidden?: boolean;
  initial_random?: string[];
  display?: Record<string, unknown>;
}

export interface SetupArchetype {
  id: string;
  name: string;
  values: Record<string, unknown>;
}

export type { ScenarioMode };

export type ScenarioStatus =
  "draft" | "publishing" | "published" | "publish_failed" | "archived";

export type ScenarioComplexityTier = ComplexityTier;

export type ScenarioPlayerCountSupport = "solo" | "multiplayer" | "both";

type ScenarioPlayerMode = "written" | "player_created";

interface ScenarioRules {
  text?: string;
}

export interface ScenarioCreate {
  title: string;
  mode: ScenarioMode;
  complexity_tier: ScenarioComplexityTier;
  logline?: string;
  player_count_support?: ScenarioPlayerCountSupport;
  estimated_playtime?: string;
  cover_image_url?: string | null;
  content_tag?: string;
  content_tags?: string[];
  genre_tags?: string[];
  narrator_persona?: string;
  world_data?: Record<string, unknown>;
  strategy_document?: Record<string, unknown>;
  setup_schema?: SetupInputField[];
  state_schema?: Record<string, StateFieldDefinition>;
  end_conditions?: unknown[];
  checkpoints?: unknown[];
  rules?: ScenarioRules;
  opening_scene?: string;
  narration_font?: string;
  narrator_voice_name?: string;
  action_chips?: string[];
  setup_archetypes?: SetupArchetype[];
  visibility?: ScenarioVisibility;
  mood_tags?: string[];
  narrator_persona_document?: LoreDocument | null;
  player_mode?: ScenarioPlayerMode;
}

export interface ScenarioUpdate {
  title?: string;
  mode?: ScenarioMode;
  status?: "draft" | "archived";
  logline?: string;
  complexity_tier?: ScenarioComplexityTier;
  player_count_support?: ScenarioPlayerCountSupport;
  estimated_playtime?: string;
  cover_image_url?: string | null;
  content_tag?: string;
  content_tags?: string[];
  genre_tags?: string[];
  narrator_persona?: string;
  world_data?: Record<string, unknown>;
  strategy_document?: Record<string, unknown>;
  setup_schema?: SetupInputField[];
  state_schema?: Record<string, StateFieldDefinition>;
  end_conditions?: unknown[];
  checkpoints?: unknown[];
  rules?: ScenarioRules;
  opening_scene?: string;
  narration_font?: string;
  narrator_voice_name?: string;
  action_chips?: string[];
  setup_archetypes?: SetupArchetype[];
  visibility?: ScenarioVisibility;
  mood_tags?: string[];
  narrator_persona_document?: LoreDocument | null;
  player_mode?: ScenarioPlayerMode;
  guide_seen_features?: string[];
  expected_content_edited_at?: string;
}

interface ScenarioSummaryResponse {
  scenario_id: string;
  creator_id: string;
  title: string;
  logline: string | null;
  mode: ScenarioMode;
  status: ScenarioStatus;
  genre_tags: string[];
  complexity_tier: ScenarioComplexityTier;
  player_count_support: ScenarioPlayerCountSupport;
  estimated_playtime: string | null;
  cover_image_url: string | null;
  content_tag: string | null;
  play_count: number;
  rating_avg: string;
  created_at: string;
  updated_at: string;
}

export interface ScenarioResponse {
  scenario_id: string;
  creator_id: string;
  creator_display_name: string | null;
  is_bookmarked: boolean;
  can_review: boolean;
  title: string;
  logline: string | null;
  mode: ScenarioMode;
  status: ScenarioStatus;
  genre_tags: string[];
  complexity_tier: ScenarioComplexityTier;
  player_count_support: ScenarioPlayerCountSupport;
  estimated_playtime: string | null;
  cover_image_url: string | null;
  content_tag: string | null;
  content_tags?: string[];
  publish_error: string | null;
  published_at: string | null;
  play_count: number;
  rating_avg: string;
  narrator_persona: string | null;
  world_data: Record<string, unknown>;
  strategy_document?: Record<string, unknown>;
  setup_schema: SetupInputField[];
  state_schema: Record<string, StateFieldDefinition>;
  end_conditions: unknown[];
  checkpoints: unknown[];
  rules: ScenarioRules;
  opening_scene: string | null;
  narration_font: string | null;
  narrator_voice_name: string | null;
  action_chips: string[];
  setup_archetypes: SetupArchetype[];
  enabled_tools?: string[];
  current_version: number;
  created_at: string;
  updated_at: string;
  visibility?: ScenarioVisibility;
  mood_tags?: string[];
  narrator_persona_document?: LoreDocument | null;
  player_mode?: ScenarioPlayerMode;
  guide_seen_features?: string[];
  content_edited_at?: string;
}

export type StudioTab = "all" | "drafts" | "published" | "archived";

export interface MyScenarioSummary extends ScenarioSummaryResponse {
  review_count: number;
  has_unpublished_changes: boolean;
  publish_error: string | null;
  content_edited_at: string;
}

export type ScenarioStatusCounts = Record<StudioTab, number>;

export interface MyScenarioListResponse {
  items: MyScenarioSummary[];
  next_cursor: string | null;
  total_count: number;
  status_counts: ScenarioStatusCounts;
}
