import { ENTITY_TYPES } from "../types/entity.types";

const MAX_TYPE_KEY_LENGTH = 30;
const FALLBACK_TYPE_KEY = "other";
const BUILT_IN_SUFFIX = "_type";

export const toEntityTypeKey = (label: string): string => {
  const slug = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^[^a-z]+/, "")
    .replace(/_+$/, "")
    .slice(0, MAX_TYPE_KEY_LENGTH);
  if (!slug) return FALLBACK_TYPE_KEY;
  const isBuiltIn = (ENTITY_TYPES as readonly string[]).includes(slug);
  return isBuiltIn ? `${slug}${BUILT_IN_SUFFIX}` : slug;
};
