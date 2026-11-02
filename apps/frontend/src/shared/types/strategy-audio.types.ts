export type StrategyUIContext =
  | "map"
  | "negotiation"
  | "letter"
  | "war_council"
  | "turn_report"
  | "event";

export type StrategicMood = "pax" | "vigilance" | "war" | "desolation";

export type AmbientTerrain = "arid" | "plains" | "coast" | "mountains";

export type StrategyStingerEvent =
  | "war_declared"
  | "treaty_signed"
  | "uprising"
  | "succession";

export type StrategyContextTrack = "court" | "study" | "tactical" | "none";

export interface StrategyAudioTarget {
  ambientTrack: AmbientTerrain;
  ambientGain: number;
  isWinterMuffled: boolean;
  strategicMood: StrategicMood;
  moodGain: number;
  contextTrack: StrategyContextTrack;
  contextGain: number;
  pendingStinger: StrategyStingerEvent | null;
}

export interface StrategyAudioEvaluatorOptions {
  minHoldDurationMs?: number;
}

export interface StrategyAudioDirectorOptions {
  volume?: number;
  isMuted?: boolean;
}
