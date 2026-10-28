import { DISPLAY_HINT_KINDS } from "@/shared/constants/display-hints";
import {
  DisplayHint,
  HintedField,
  HudHints,
} from "@/shared/types/display-hints.types";

const HINT_KINDS: readonly string[] = DISPLAY_HINT_KINDS;

const isDisplayHint = (value: unknown): value is DisplayHint =>
  typeof value === "object" &&
  value !== null &&
  HINT_KINDS.includes((value as { kind?: unknown }).kind as string);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

interface FoundHint extends HintedField<DisplayHint> {
  options: string[];
}

// Enum options are plain strings or `{ value }` objects.
function readEnumOptions(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((option: unknown) => {
    if (typeof option === "string") return [option];
    if (isRecord(option) && "value" in option) return [String(option.value)];
    return [];
  });
}

function collectHints(
  fields: Record<string, unknown>,
  prefix: string,
  into: FoundHint[],
): void {
  for (const [name, field] of Object.entries(fields)) {
    if (!isRecord(field)) continue;
    const path = `${prefix}${name}`;
    if (isDisplayHint(field.display)) {
      into.push({ path, hint: field.display, options: readEnumOptions(field.options) });
    }
    if (isRecord(field.fields)) collectHints(field.fields, `${path}.`, into);
  }
}

// Computed once per snapshot; the HUD then reads values from state by path.
export function readDisplayHints(stateSchema: Record<string, unknown>): HudHints {
  const found: FoundHint[] = [];
  collectHints(stateSchema, "", found);
  const hints: HudHints = { meters: [] };
  for (const entry of found) {
    if (entry.hint.kind === "clock") {
      hints.clock ??= { path: entry.path, hint: entry.hint };
    } else if (entry.hint.kind === "tier") {
      hints.tier ??= {
        path: entry.path,
        hint: entry.hint,
        options: entry.options,
      };
    } else {
      hints.meters.push({ path: entry.path, hint: entry.hint });
    }
  }
  return hints;
}

export function getStateValue(
  state: Record<string, unknown>,
  path: string,
): unknown {
  let current: unknown = state;
  for (const segment of path.split(".")) {
    if (!isRecord(current)) return undefined;
    current = current[segment];
  }
  return current;
}
