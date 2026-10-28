import { MeterTier } from "@/shared/types/display-hints.types";

// Tiers are authored strictly descending by `min`; the first one the value
// reaches wins, and a tier without `min` catches everything below.
export function resolveMeterTier(
  tiers: MeterTier[] | undefined,
  value: number,
): string | null {
  const reached = tiers?.find((tier) => tier.min === undefined || value >= tier.min);
  return reached?.name ?? null;
}
