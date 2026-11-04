import type {
  CrowdMood,
  ExhaustionBucket,
  MoraleBucket,
} from "../types/battleSpeech.types";

export const STAGE_FIGURE_COUNT = 14;

export const MORALE_FIGURE_CLASSES: Record<MoraleBucket, string> = {
  broken: "opacity-30",
  shaken: "opacity-50",
  steady: "opacity-70",
  resolute: "opacity-90",
  fervent: "opacity-100 scale-y-110",
};

export const EXHAUSTION_FIGURE_CLASSES: Record<ExhaustionBucket, string> = {
  fresh: "translate-y-0",
  tired: "translate-y-1",
  spent: "translate-y-2 rotate-3",
};

export const REACTION_FIGURE_CLASSES: Record<CrowdMood, string> = {
  hush: "motion-safe:duration-700",
  murmur: "motion-safe:animate-pulse",
  protest: "-rotate-6 motion-safe:animate-pulse",
  cheer: "-translate-y-2 motion-safe:animate-bounce",
};
