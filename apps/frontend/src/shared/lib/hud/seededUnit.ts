const FNV_OFFSET_BASIS = 2166136261;
const FNV_PRIME = 16777619;
const UINT32_RANGE = 4294967296;
const MIX_SHIFT_HIGH = 16;
const MIX_SHIFT_MID = 13;
const MIX_MULTIPLIER_A = 0x85ebca6b;
const MIX_MULTIPLIER_B = 0xc2b2ae35;

// Deterministic value in [0, 1) for a seed and a number, so the same inputs
// always draw the same result across renders and reloads.
export function seededUnit(seed: string, value: number): number {
  const text = `${seed}:${value}`;
  let hash = FNV_OFFSET_BASIS;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, FNV_PRIME);
  }
  hash ^= hash >>> MIX_SHIFT_HIGH;
  hash = Math.imul(hash, MIX_MULTIPLIER_A);
  hash ^= hash >>> MIX_SHIFT_MID;
  hash = Math.imul(hash, MIX_MULTIPLIER_B);
  hash ^= hash >>> MIX_SHIFT_HIGH;
  return (hash >>> 0) / UINT32_RANGE;
}
