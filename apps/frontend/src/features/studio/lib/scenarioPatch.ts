import { NAME_SETUP_FIELD } from "../constants/guideChips";
import { LOGLINE_MAX_LENGTH, TITLE_MAX_LENGTH } from "../constants/guideLimits";
import type { ScenarioCreate, ScenarioUpdate } from "../types/scenario.types";
import type { ScenarioFieldsPatch } from "../types/scenarioPatch.types";

const isMeaningful = (value: unknown): boolean => {
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) return value.some(isMeaningful);
  if (typeof value === "object" && value !== null) {
    return Object.values(value).some(isMeaningful);
  }
  return false;
};

export const hasFirstWord = (patch: ScenarioFieldsPatch): boolean =>
  Object.values(patch).some(isMeaningful);

export const isEmptyPatch = (patch: ScenarioFieldsPatch): boolean =>
  Object.keys(patch).length === 0;

export const mergeScenarioPatches = (
  base: ScenarioFieldsPatch,
  next: ScenarioFieldsPatch,
): ScenarioFieldsPatch => {
  const merged: ScenarioFieldsPatch = { ...base, ...next };
  if (base.worldData || next.worldData) {
    merged.worldData = { ...base.worldData, ...next.worldData };
  }
  return merged;
};

export const subtractScenarioPatch = (
  base: ScenarioFieldsPatch,
  written: ScenarioFieldsPatch,
): ScenarioFieldsPatch => {
  const { worldData: baseWorldData, ...baseFields } = base;
  const { worldData: writtenWorldData, ...writtenFields } = written;
  const remaining: ScenarioFieldsPatch = Object.fromEntries(
    Object.entries(baseFields).filter(([key]) => !(key in writtenFields)),
  );
  const remainingWorldData = Object.fromEntries(
    Object.entries(baseWorldData ?? {}).filter(([key]) => !(key in (writtenWorldData ?? {}))),
  );
  if (Object.keys(remainingWorldData).length === 0) return remaining;
  return { ...remaining, worldData: remainingWorldData };
};

export const buildScenarioUpdate = (
  patch: ScenarioFieldsPatch,
  currentWorldData: Record<string, unknown>,
): ScenarioUpdate => {
  const { worldData, ...fields } = patch;
  if (!worldData) return fields;
  return { ...fields, world_data: { ...currentWorldData, ...worldData } };
};

const clampText = (value: string, maxLength: number): string =>
  value.slice(0, maxLength);

export const buildDraftPayload = (patch: ScenarioFieldsPatch): ScenarioCreate => {
  const { worldData, title, logline, ...fields } = patch;
  return {
    setup_schema: [NAME_SETUP_FIELD],
    ...fields,
    title: clampText(title ?? "", TITLE_MAX_LENGTH),
    ...(logline === undefined
      ? {}
      : { logline: clampText(logline, LOGLINE_MAX_LENGTH) }),
    ...(worldData ? { world_data: worldData } : {}),
    mode: "newbie",
    complexity_tier: "newbie",
    visibility: "private",
  };
};
