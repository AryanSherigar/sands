import type { RuleSheetItem } from "@/shared/types/rule-sheet.types";
import { ReaderTheme } from "@/shared/types/readerPreferences.types";
import { ScenarioMood } from "@/shared/types/audio.types";
import {
  PendingCheckState,
  RuleCheckEventPayload,
} from "@/shared/types/check.types";
import { HudHints } from "@/shared/types/display-hints.types";
import { MinigameEventPayload } from "@/shared/types/minigame.types";

export type ActionMode = "say" | "do" | "story" | "see";

export type EBookTheme = ReaderTheme;

export type EntityType =
  "character" | "location" | "item" | "faction" | "organization";

export interface EntityAttributeSchemaField {
  type: "string" | "number" | "boolean" | "enum";
  label?: string;
}

export interface MasterEntity {
  entity_id: string;
  entity_type: EntityType;
  canonical_name: string;
  aliases: string[];
  description: string | null;
  attributes_schema: Record<string, EntityAttributeSchemaField>;
  obtainable: boolean | null;
  // Live values, resolved from PlaythroughResponse.state.entities[entity_id].
  attributes: Record<string, unknown>;
}

// Shape of the `playthrough_ended` SSE event payload (TRS's
// response_streamer.playthrough_ended_event), emitted once when a turn
// matches a scenario end condition.
export interface PlaythroughEndedPayload {
  outcome_tag: "win" | "lose";
  outcome_title: string;
  outcome_text: string;
}

export interface Objective {
  outcome_title: string;
  outcome_tag: "win" | "lose";
  outcome_text: string;
}

export interface PlayerStat {
  key: string;
  label: string;
  value: unknown;
}

export interface StatChange {
  path: string;
  label: string;
  before?: string | number | boolean | null;
  after?: string | number | boolean | null;
  delta?: number | null;
}

export interface InventoryChange {
  path: string;
  entity_id: string;
  entity_display_name: string;
}

export interface ChapterDelta {
  stat_changes: StatChange[];
  inventory_changes: InventoryChange[];
}

export interface TurnLogItem {
  id: string;
  turn_number: number;
  action_mode: ActionMode;
  action_text: string;
  narration_text: string;
  created_at: string;
  // Populated for master mode: live via SSE, or reconstructed from
  // tool_calls on reload — see utils/chapterDelta.ts.
  chapter_delta?: ChapterDelta;
  // Populated for a "see" action turn that generated a scene image, live via
  // the `scene_image` SSE event or from the persisted TurnLog on reload.
  image_url?: string;
  // Populated only when voice output was on for this turn, live via the
  // `narration_audio` SSE event or from the persisted TurnLog on reload.
  audio_url?: string;
}

export interface CharacterSetupField {
  key: string;
  label: string;
  value: string;
}

export interface StoryCard {
  id: string;
  title: string;
  category: string;
  content: string;
}

export interface PlaythroughData {
  playthrough_id: string;
  scenario_id: string;
  scenario_title: string;
  mode: "newbie" | "master" | "strategy";
  initial_mood?: ScenarioMood;
  // Per-scenario mood → track URL, pinned into scenario_snapshot at
  // playthrough creation (ADR-8). Always a real, playable URL for every
  // mood -- the backend resolves an untouched slot to its built-in default
  // track. A null entry can still appear in a snapshot frozen before that
  // guarantee existed; getMoodTrackUrl() is the safety net for those.
  music_tracks?: Partial<Record<ScenarioMood, string | null>>;
  // Tension tier value → track URL, pinned like music_tracks. Present only for
  // a scenario whose tier hint declares a track_map; a tier without an entry
  // (or whose file fails to load) plays its mood_map default instead.
  tier_tracks?: Record<string, string>;
  narration_font?: string | null;
  // Creator-authored quick-insert phrases for the turn input, pinned from
  // scenario_snapshot at playthrough creation (ADR-8). [] for newbie
  // (Studio never exposes chip authoring outside master mode) or a master
  // scenario whose creator added none.
  action_chips: string[];
  // Scenario-authored job lines shown above the rules (world_data.duties).
  duties?: string[];
  // Tool keys pinned from scenario_snapshot.enabled_tools at playthrough
  // creation (ADR-016). [] for a snapshot that predates tools.
  enabled_tools: string[];
  creator_name: string;
  cover_image_url?: string;
  opening_premise: string;
  world_lore: string;
  key_facts: string[];
  story_cards: StoryCard[];
  character_name: string;
  custom_fields: CharacterSetupField[];
  turns: TurnLogItem[];
  is_spectator: boolean;
  // The requesting user's own participant_id — required by POST /v1/turn.
  // Absent for spectators, who never submit turns.
  participant_id: string | null;
  // Multiplayer turn-order gate: false when it's another participant's turn.
  // Always true for solo playthroughs and irrelevant for spectators.
  can_act: boolean;
  // Display name of whoever acts next, for the "Waiting for X..." bottom-bar
  // state when !can_act. Null for solo playthroughs (can_act is always true).
  next_actor_label: string | null;
  // Master-mode-only fields — [] for newbie.
  entities: MasterEntity[];
  active_conditions: string[];
  objectives: Objective[];
  player_stats: PlayerStat[];
  player_inventory: MasterEntity[];
  // Populated from state._pending_minigame on load/reload so a minigame the
  // player left mid-resolution resumes on mount, without waiting for a new
  // SSE "minigame" event (see MinigameOverlay's reload-resume behaviour).
  pending_minigame: MinigameEventPayload | null;
  // Populated from state._pending_check on load/reload, same resume pattern
  // as pending_minigame above — see CheckPromptOverlay. resolved_roll is set
  // only if the player already clicked "attempt" before leaving/reloading.
  pending_check: PendingCheckState | null;
  // A rule check (timed prompt) left open on load/reload, read from the same
  // state._pending_check marker (kind != dice), and the server clock at load so
  // the remaining time can be derived.
  pending_rule_check: RuleCheckEventPayload | null;
  server_time_ms: number | null;
  // The visible part of Playthrough.state (hidden fields never reach the
  // client), kept current by the `state_update` event; the HUD reads its values
  // by path. hud_hints are the display hints of the pinned state_schema.
  state: Record<string, unknown>;
  hud_hints: HudHints;
  // The clipboard of the `rule_sheet` tool: only rules already revealed, kept
  // current by the `state_update` event. [] when the tool is off.
  rule_sheet: RuleSheetItem[];
  // Master-mode-only; populated once an end condition matches, either from a
  // live "playthrough_ended" SSE event or from PlaythroughResponse on
  // load/reload. null for newbie and for an in-progress master playthrough.
  ended_outcome_tag: "win" | "lose" | null;
  ended_outcome_title: string | null;
  ended_outcome_text: string | null;
}

/** Payload of the `memory_degraded` SSE event, emitted before `done` when story
 * memory is behind. `reasons` are stable codes from the memory service and TRS. */
export interface MemoryDegradedPayload {
  reasons: string[];
}

/** Payload of the `input_truncated` SSE event, the first event of a turn whose
 * action text was cut to the server's size cap. Carries lengths only. */
export interface InputTruncatedPayload {
  original_length: number;
  max_length: number;
}
