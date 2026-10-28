export const MAX_VIGNETTE_STRENGTH = 0.55;

// The first tier has no vignette; the last has the full strength.
export function tensionVignetteStrength(index: number, count: number): number {
  if (count <= 1) return 0;
  return (index / (count - 1)) * MAX_VIGNETTE_STRENGTH;
}
