// Master-mode Minigames shapes, shared between studio/ (authoring) and
// play/ (gameplay) — features never import from each other, so this shape
// lives in shared/ per CLAUDE.md. See docs/specs/master-mode-minigames.spec.md.

import type { StateMutation } from "./stateMutation.types";

export type { StateMutation } from "./stateMutation.types";

// Must equal MINIGAME_TYPES in apps/core-api/app/models/minigame.py;
// apps/core-api/tests/test_frontend_constants_drift.py parses this array.
export const MINIGAME_TYPES = ["dodge", "lockpick", "rhythm_composure"] as const;

export type MinigameType = (typeof MINIGAME_TYPES)[number];
export type OutcomeMode = "binary" | "tiered";
export type MinigameOutcomeTag = "win" | "lose" | "timeout";

export interface TieredOutcomeRange {
  min_score: number;
  max_score: number;
  mutation: StateMutation;
}

/** Curated hazards only. Their collision geometry is deliberately not authorable. */
type DodgePattern = "rain" | "ring" | "beam" | "homing";
export type DodgePlayerStyle = "soul" | "heart" | "spark";
export type DodgeObstacleStyle = "ash" | "neon" | "crystal";
export type DodgeBackground = "void" | "ember" | "midnight";
export type DodgeTexture = "none" | "grain" | "stars";
export type DodgePalette = "ashfall" | "ember" | "aurora";

interface DodgePerformanceThresholds {
  excellent_min_health: number;
  survive_min_health: number;
}

export interface DodgeAudioSettings {
  /** Storage URL returned by the application's uploader; external URLs are not accepted. */
  music_asset_url: string | null;
  volume: number;
  muted: boolean;
}

interface DodgeCopy {
  instructions: string;
  start_text: string;
  win_text: string;
  lose_text: string;
}

export interface DodgeConfigShape {
  /** Allows readers to safely evolve this presentation-only contract. */
  version?: number;
  difficulty: number; // 1-5
  duration_seconds?: number;
  health?: number;
  invulnerability_ms?: number;
  enabled_patterns?: DodgePattern[];
  pattern_order?: DodgePattern[];
  performance_thresholds?: DodgePerformanceThresholds;
  player_style?: DodgePlayerStyle;
  obstacle_style?: DodgeObstacleStyle;
  obstacle_color?: string;
  background?: DodgeBackground;
  texture?: DodgeTexture;
  palette?: DodgePalette;
  background_asset_url?: string | null;
  audio?: DodgeAudioSettings;
  copy?: DodgeCopy;
}

export const DEFAULT_DODGE_CONFIG: DodgeConfigShape = {
  version: 1,
  difficulty: 3,
  duration_seconds: 15,
  health: 3,
  invulnerability_ms: 1000,
  enabled_patterns: ["rain", "ring", "beam", "homing"],
  pattern_order: ["rain", "ring", "beam", "homing"],
  performance_thresholds: { excellent_min_health: 3, survive_min_health: 1 },
  player_style: "soul",
  obstacle_style: "ash",
  obstacle_color: "#ff8a65",
  background: "void",
  texture: "none",
  palette: "ashfall",
  background_asset_url: null,
  audio: { music_asset_url: null, volume: 0.7, muted: false },
  copy: {
    instructions: "Survive the ashfall. Move with WASD and avoid hazards.",
    start_text: "Start",
    win_text: "Survived!",
    lose_text: "Defeated...",
  },
};

interface LockpickCopy {
  instructions: string;
  start_text: string;
  win_text: string;
  lose_text: string;
}

export interface LockpickConfigShape {
  version?: number;
  difficulty: number; // 1-5
  picks?: number;     // available picks (health pool), 1-10, default 3
  copy?: LockpickCopy;
}

export const DEFAULT_LOCKPICK_CONFIG: LockpickConfigShape = {
  version: 1,
  difficulty: 3,
  picks: 3,
  copy: {
    instructions: "Align the pick with the sweet spot and hold.",
    start_text: "Begin",
    win_text: "Unlocked!",
    lose_text: "Pick broken.",
  },
};

export type ComposureKey = "W" | "A" | "S" | "D";
export type ComposureAudioProfile = "chase" | "hum";

interface ComposureTexts {
  instructions: string;
  start_text: string;
  win_text: string;
  lose_text: string;
}

// Tool `composure`: a panic-rhythm challenge. Mirrors ComposureConfig in
// apps/core-api/app/models/minigame.py.
export interface ComposureConfigShape {
  version?: number;
  target_bpm: number; // 30-120
  beats_to_win: number; // 3-12 consecutive hits
  tolerance_ms: number; // 80-400
  max_strikes: number; // 1-5
  keys: ComposureKey[];
  audio_profile: ComposureAudioProfile;
  texts: ComposureTexts;
}

export const DEFAULT_COMPOSURE_CONFIG: ComposureConfigShape = {
  version: 1,
  target_bpm: 55,
  beats_to_win: 5,
  tolerance_ms: 180,
  max_strikes: 2,
  keys: ["W", "A", "S", "D"],
  audio_profile: "hum",
  texts: {
    instructions: "Press the lit key on the beat. Stay calm.",
    start_text: "Begin",
    win_text: "You kept your composure.",
    lose_text: "Your composure broke.",
  },
};

// The play-time payload delivered via the "minigame" SSE event. Deliberately
// carries no mutation/outcome data — TRS alone decides state consequences;
// the client only ever reports what happened (see MinigameResultPayload).
export interface MinigameEventPayload {
  minigame_id: string;
  /** Server-issued identifier for this unresolved encounter. Reused on retries. */
  attempt_id?: string;
  minigame_type: MinigameType;
  label: string;
  dodge_config?: DodgeConfigShape | null;
  lockpick_config?: LockpickConfigShape | null;
  composure_config?: ComposureConfigShape | null;
  timeout_seconds: number;
}

export interface MinigameResultPayload {
  minigame_id: string;
  outcome_tag: MinigameOutcomeTag;
  score?: number;
  /** Must be the attempt_id supplied in MinigameEventPayload when available. */
  attempt_id?: string;
}

// What a minigame implementation (DodgeMinigame) hands
// back on completion — everything MinigameResultPayload needs except
// minigame_id, which the caller (MinigameOverlay in play/, or a Studio
// preview) already knows and attaches itself.
export type MinigameOutcomeResult = Omit<MinigameResultPayload, "minigame_id">;
