import type { StateFieldDefinition } from "../types/scenario.types";
import type { NewTrackedValue } from "../types/trackedValue.types";

export const RESERVED_VALUE_KEYS: ReadonlySet<string> = new Set([
  "current_location_id",
  "discovered_location_ids",
  "entities",
  "rule_status",
  "rule_flags",
]);
const KEY_SEPARATOR = "_";
const NON_KEY_CHARACTERS = /[^a-z0-9]+/g;
const FALLBACK_KEY = "value";
const DEFAULT_NUMBER_START = 0;

export const buildValueKey = (name: string, takenKeys: ReadonlySet<string>): string => {
  const base =
    name.trim().toLowerCase().replace(NON_KEY_CHARACTERS, KEY_SEPARATOR).replace(/^_+|_+$/g, "") ||
    FALLBACK_KEY;
  let candidate = base;
  let suffix = 2;
  while (takenKeys.has(candidate) || RESERVED_VALUE_KEYS.has(candidate)) {
    candidate = `${base}${KEY_SEPARATOR}${suffix}`;
    suffix += 1;
  }
  return candidate;
};

const defaultInitial = (input: NewTrackedValue): number | boolean | string => {
  if (input.initial !== undefined) return input.initial;
  if (input.kind === "boolean") return false;
  if (input.kind === "enum") return input.options?.[0] ?? "";
  return input.min ?? DEFAULT_NUMBER_START;
};

export const buildStateField = (input: NewTrackedValue): StateFieldDefinition => ({
  type: input.kind,
  label: input.name.trim(),
  initial: defaultInitial(input),
  ...(input.kind === "number" && input.min !== undefined ? { min: input.min } : {}),
  ...(input.kind === "number" && input.max !== undefined ? { max: input.max } : {}),
  ...(input.kind === "enum" ? { options: input.options ?? [] } : {}),
  ...(input.description ? { description: input.description } : {}),
  ...(input.display ? { display: input.display } : {}),
});
