import { PLAYTEST_READOUT_HIDDEN } from "../constants/playtest";
import type { StateFieldDefinition } from "../types/scenario.types";
import type { ValueKind, ValueOption } from "../types/sentence.types";

export interface ReadoutRow {
  path: string;
  label: string;
  text: string;
}

const ENTITIES_BUCKET = "entities";

const readNested = (source: unknown, parts: readonly string[]): unknown =>
  parts.reduce<unknown>(
    (current, part) =>
      typeof current === "object" && current !== null
        ? (current as Record<string, unknown>)[part]
        : undefined,
    source,
  );

export const readStateValue = (state: Record<string, unknown>, path: string): unknown => {
  const parts = path.split(".");
  const direct = readNested(state, parts);
  if (direct !== undefined) return direct;
  return readNested(state[ENTITIES_BUCKET], parts);
};

const formatValue = (value: unknown, kind: ValueKind): string => {
  if (kind === "boolean") return value === true ? "yes" : "no";
  return String(value);
};

export const listHiddenPaths = (
  schema: Record<string, StateFieldDefinition>,
  prefix = "",
  isParentHidden = false,
): Set<string> => {
  const hidden = new Set<string>();
  Object.entries(schema).forEach(([key, field]) => {
    const path = `${prefix}${key}`;
    const isHidden = isParentHidden || field.hidden === true;
    if (isHidden) hidden.add(path);
    listHiddenPaths(field.fields ?? {}, `${path}.`, isHidden).forEach((nested) => hidden.add(nested));
  });
  return hidden;
};

export const buildReadoutRows = (
  options: readonly ValueOption[],
  state: Record<string, unknown>,
  hiddenPaths: ReadonlySet<string>,
): ReadoutRow[] =>
  options.flatMap((option) => {
    if (hiddenPaths.has(option.path)) {
      return [{ path: option.path, label: option.label, text: PLAYTEST_READOUT_HIDDEN }];
    }
    const value = readStateValue(state, option.path);
    if (value === undefined || value === null) return [];
    return [{ path: option.path, label: option.label, text: formatValue(value, option.kind) }];
  });
