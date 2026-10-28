// Display hints a creator attaches to a state_schema field (tool `status_hud`).
// Mirrors apps/core-api/app/services/display_hints.py.

export type ClockFormat = "12h" | "24h";

export interface ClockGlitch {
  source: string;
  below: number;
  chance: number;
}

export interface ClockHint {
  kind: "clock";
  label: string;
  start: string;
  format: ClockFormat;
  glitch?: ClockGlitch;
}

export interface MeterTier {
  name: string;
  min?: number;
}

export interface MeterEffects {
  moderate_below?: number;
  critical_below?: number;
  intrusive_below?: number;
  intrusive_thoughts?: string[];
}

export interface MeterHint {
  kind: "meter";
  label: string;
  clamp_min: number;
  clamp_max: number;
  tiers?: MeterTier[];
  effects?: MeterEffects;
}

export interface TierHint {
  kind: "tier";
  label: string;
  mood_map?: Record<string, string>;
  track_map?: Record<string, string>;
}

export type DisplayHint = ClockHint | MeterHint | TierHint;

export interface HintedField<THint extends DisplayHint> {
  path: string;
  hint: THint;
}

interface HintedTier extends HintedField<TierHint> {
  options: string[];
}

export interface HudHints {
  clock?: HintedField<ClockHint>;
  meters: HintedField<MeterHint>[];
  tier?: HintedTier;
}
