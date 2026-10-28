import { MeterEffects } from "@/shared/types/display-hints.types";

export type SanityBand = "none" | "moderate" | "critical";

// critical_below <= value < moderate_below is the moderate band; below
// critical_below is critical. A threshold the creator left out never triggers.
// The state value is used as is, so a floor of -100 still reads as critical.
export function resolveSanityBand(
  value: number,
  effects: MeterEffects | undefined,
): SanityBand {
  if (!effects) return "none";
  const { critical_below: critical, moderate_below: moderate } = effects;
  if (critical !== undefined && value < critical) return "critical";
  if (moderate !== undefined && value < moderate) return "moderate";
  return "none";
}
