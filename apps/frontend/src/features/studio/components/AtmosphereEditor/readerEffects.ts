import type { MeterEffects } from "@/shared/types/display-hints.types";

export const MAX_INTRUSIVE_THOUGHTS = 8;
export const MAX_THOUGHT_LENGTH = 60;
export const THRESHOLDS = [
  ["moderate_below", "Distort words below"],
  ["critical_below", "Eerie face below"],
  ["intrusive_below", "Intrusive thoughts below"],
] as const;

export const effectsProblems = (effects: MeterEffects): string[] => {
  const problems: string[] = [];
  const { moderate_below: moderate, critical_below: critical } = effects;
  if (moderate !== undefined && critical !== undefined && critical > moderate) {
    problems.push("The eerie face threshold cannot be above the distortion threshold.");
  }
  const thoughts = effects.intrusive_thoughts ?? [];
  if (thoughts.length > MAX_INTRUSIVE_THOUGHTS) {
    problems.push(`Use at most ${MAX_INTRUSIVE_THOUGHTS} intrusive thoughts.`);
  }
  if (thoughts.some((text) => !text.trim() || text.length > MAX_THOUGHT_LENGTH)) {
    problems.push(`Each thought needs 1 to ${MAX_THOUGHT_LENGTH} characters.`);
  }
  return problems;
};

