import type {
  ClockHint,
  MeterHint,
  MeterTier,
  TierHint,
} from "@/shared/types/display-hints.types";

const START_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

export const DEFAULT_CLOCK: ClockHint = {
  kind: "clock",
  label: "Shift",
  start: "23:00",
  format: "12h",
};
export const DEFAULT_METER: MeterHint = {
  kind: "meter",
  label: "Meter",
  clamp_min: 0,
  clamp_max: 100,
};
export const DEFAULT_TIER: TierHint = { kind: "tier", label: "Tension" };

const isValidStart = (start: string): boolean => START_PATTERN.test(start);

const tierProblems = (tiers: MeterTier[]): string[] => {
  const minimums = tiers.flatMap((tier) => (tier.min === undefined ? [] : [tier.min]));
  const isDescending = minimums.every(
    (value, index) => index === 0 || value < minimums[index - 1],
  );
  return isDescending ? [] : ["Tier minimums must go down from the first to the last."];
};

export const meterProblems = (hint: MeterHint): string[] => [
  ...(hint.label.trim() ? [] : ["The meter needs a label."]),
  ...(hint.clamp_min < hint.clamp_max
    ? []
    : ["The lowest shown value must be below the highest."]),
  ...tierProblems(hint.tiers ?? []),
];

export const clockProblems = (hint: ClockHint): string[] => [
  ...(hint.label.trim() ? [] : ["The clock needs a label."]),
  ...(isValidStart(hint.start) ? [] : ["The start time is written HH:MM, e.g. 23:00."]),
  ...(hint.glitch && (hint.glitch.chance < 0 || hint.glitch.chance > 1)
    ? ["The glitch chance is between 0 and 1."]
    : []),
];
