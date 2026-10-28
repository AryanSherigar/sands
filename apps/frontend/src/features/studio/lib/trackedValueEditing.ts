import {
  DEFAULT_CLOCK_FORMAT,
  DEFAULT_CLOCK_START,
  DEFAULT_LEVELS,
} from "../constants/valueQuickAdd";
import type { StateFieldDefinition } from "../types/scenario.types";
import type { ValueKind } from "../types/sentence.types";
import type { NewTrackedValue } from "../types/trackedValue.types";
import { buildStateField } from "./trackedValueSchema";
import { enumOptionValues } from "./stateSchemaFields";

export type PlayerSees = "bar" | "plain" | "levels" | "clock" | "hidden";

export interface HudAvailability {
  isClockTaken: boolean;
  isLevelsTaken: boolean;
}

type Display = Record<string, unknown>;

const readKind = (field: StateFieldDefinition): string | undefined => {
  const kind = field.display?.kind;
  return typeof kind === "string" ? kind : undefined;
};

export const readPlayerSees = (field: StateFieldDefinition): PlayerSees => {
  if (field.hidden === true) return "hidden";
  const kind = readKind(field);
  if (kind === "clock") return "clock";
  if (kind === "tier") return "levels";
  if (kind === "meter") return Array.isArray(field.display?.tiers) ? "levels" : "bar";
  return "plain";
};

export const hasBounds = (field: StateFieldDefinition): boolean =>
  typeof field.min === "number" && typeof field.max === "number" && field.min < field.max;

const stripPresentation = (field: StateFieldDefinition): StateFieldDefinition => {
  const { display: _display, hidden: _hidden, ...rest } = field;
  return rest;
};

const displayLabel = (field: StateFieldDefinition): string => field.label?.trim() || "Value";

const buildMeter = (field: StateFieldDefinition, withLevels: boolean): Display => {
  const current = readKind(field) === "meter" ? (field.display as Display) : {};
  const meter: Display = {
    ...current,
    kind: "meter",
    label: displayLabel(field),
    clamp_min: field.min,
    clamp_max: field.max,
  };
  if (!withLevels) {
    delete meter.tiers;
    return meter;
  }
  meter.tiers = Array.isArray(current.tiers) ? current.tiers : DEFAULT_LEVELS.map((level) => ({ ...level }));
  return meter;
};

const buildClock = (field: StateFieldDefinition): Display =>
  readKind(field) === "clock"
    ? { ...(field.display as Display), label: displayLabel(field) }
    : { kind: "clock", label: displayLabel(field), start: DEFAULT_CLOCK_START, format: DEFAULT_CLOCK_FORMAT };

const buildTier = (field: StateFieldDefinition): Display =>
  readKind(field) === "tier"
    ? { ...(field.display as Display), label: displayLabel(field) }
    : { kind: "tier", label: displayLabel(field) };

export const applyPlayerSees = (field: StateFieldDefinition, sees: PlayerSees): StateFieldDefinition => {
  const base = stripPresentation(field);
  if (sees === "hidden") return { ...base, hidden: true };
  if (sees === "plain") return base;
  if (sees === "clock") return { ...base, display: buildClock(field) };
  if (sees === "levels" && field.type === "enum") return { ...base, display: buildTier(field) };
  return { ...base, display: buildMeter(field, sees === "levels") };
};

export const listPlayerSeesChoices = (
  field: StateFieldDefinition,
  availability: HudAvailability,
): Array<{ value: PlayerSees; isDisabled: boolean }> => {
  const current = readPlayerSees(field);
  if (field.type === "number") {
    const canShowBar = hasBounds(field);
    return [
      { value: "bar", isDisabled: !canShowBar && current !== "bar" },
      { value: "plain", isDisabled: false },
      { value: "levels", isDisabled: (!canShowBar || availability.isLevelsTaken) && current !== "levels" },
      { value: "clock", isDisabled: availability.isClockTaken && current !== "clock" },
      { value: "hidden", isDisabled: false },
    ];
  }
  if (field.type === "enum") {
    return [
      { value: "plain", isDisabled: false },
      { value: "levels", isDisabled: availability.isLevelsTaken && current !== "levels" },
      { value: "hidden", isDisabled: false },
    ];
  }
  return [
    { value: "plain", isDisabled: false },
    { value: "hidden", isDisabled: false },
  ];
};

export const usesStatusHud = (field: StateFieldDefinition): boolean =>
  field.display !== undefined || (field.type === "number" && field.hidden !== true);

const withDisplayPatch = (field: StateFieldDefinition, patch: Display): StateFieldDefinition =>
  field.display ? { ...field, display: { ...field.display, ...patch } } : field;

export const renameField = (field: StateFieldDefinition, name: string): StateFieldDefinition => {
  const renamed = { ...field, label: name };
  return withDisplayPatch(renamed, { label: name.trim() || "Value" });
};

const clampInitial = (field: StateFieldDefinition): StateFieldDefinition => {
  if (typeof field.initial !== "number") return field;
  const floor = field.min ?? Number.NEGATIVE_INFINITY;
  const ceiling = field.max ?? Number.POSITIVE_INFINITY;
  return { ...field, initial: Math.min(ceiling, Math.max(floor, field.initial)) };
};

const syncMeterBounds = (field: StateFieldDefinition): StateFieldDefinition => {
  if (readKind(field) !== "meter") return field;
  if (!hasBounds(field)) return applyPlayerSees(field, "plain");
  return withDisplayPatch(field, { clamp_min: field.min, clamp_max: field.max });
};

export const setBound = (
  field: StateFieldDefinition,
  bound: "min" | "max",
  value: number | undefined,
): StateFieldDefinition => {
  const { [bound]: _previous, ...rest } = field;
  const next = value === undefined ? rest : { ...rest, [bound]: value };
  return syncMeterBounds(clampInitial(next));
};

export const setOptions = (field: StateFieldDefinition, options: string[]): StateFieldDefinition => {
  const initial = typeof field.initial === "string" && options.includes(field.initial) ? field.initial : (options[0] ?? "");
  return { ...field, options, initial };
};

export const readChoices = (field: StateFieldDefinition): string[] => enumOptionValues(field.options);

export const changeKind = (field: StateFieldDefinition, kind: ValueKind): StateFieldDefinition => {
  const input: NewTrackedValue = {
    name: field.label ?? "",
    kind,
    ...(kind === "enum" ? { options: ["Option one", "Option two"] } : {}),
    ...(field.description ? { description: field.description } : {}),
  };
  return buildStateField(input);
};

export const isNeedingDetails = (field: StateFieldDefinition): boolean => !field.description?.trim();

export const isEditableValue = (field: StateFieldDefinition): boolean =>
  field.type === "number" || field.type === "boolean" || field.type === "enum";
