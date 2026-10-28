import { PLAYTEST_PLAYER_NAME } from "../constants/playtest";
import type { SetupInputField } from "@/shared/types/scenario.types";

type SetupValues = Record<string, unknown>;

export const needsSetupForm = (fields: SetupInputField[]): boolean =>
  fields.some((field) => !field.is_character_name);

const readDefault = (field: SetupInputField): unknown => {
  if (field.is_character_name) return PLAYTEST_PLAYER_NAME;
  if (field.defaultValue !== undefined && field.defaultValue !== "") return field.defaultValue;
  return field.type === "multi_select" ? [] : "";
};

export const buildInitialSetupValues = (fields: SetupInputField[]): SetupValues =>
  Object.fromEntries(fields.map((field) => [field.key, readDefault(field)]));

export const getMissingRequiredFields = (
  fields: SetupInputField[],
  values: SetupValues,
): SetupInputField[] =>
  fields.filter((field) => {
    const value = values[field.key];
    const isEmpty = value === undefined || value === "" || (Array.isArray(value) && value.length === 0);
    return field.required && isEmpty;
  });

export const readOpeningText = (playthrough: {
  state?: Record<string, unknown>;
  scenario_snapshot?: Record<string, unknown>;
}): string => {
  const narrative = playthrough.state?.narrative as { opening_prompt?: unknown } | undefined;
  const rendered = narrative?.opening_prompt;
  if (typeof rendered === "string" && rendered.trim()) return rendered;
  const snapshotScene = playthrough.scenario_snapshot?.opening_scene;
  return typeof snapshotScene === "string" ? snapshotScene : "";
};
