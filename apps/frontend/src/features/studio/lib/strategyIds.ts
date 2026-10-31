import {
  STRATEGY_ID_FALLBACK_PREFIX,
  STRATEGY_ID_SLUG_LENGTH,
} from "../constants/strategyAuthoring";

export const makeUniqueId = (name: string, takenIds: readonly string[]): string => {
  const slug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, STRATEGY_ID_SLUG_LENGTH);
  const base = /^[a-z]/.test(slug) && slug.length >= 2 ? slug : `${STRATEGY_ID_FALLBACK_PREFIX}${slug}`;
  let candidate = base;
  for (let suffix = 2; takenIds.includes(candidate); suffix += 1) {
    candidate = `${base}_${suffix}`;
  }
  return candidate;
};
