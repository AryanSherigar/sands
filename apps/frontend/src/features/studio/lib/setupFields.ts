import type { SetupQuickAdd } from "../constants/guideChips";
import type { SetupInputField, SetupInputOption } from "@/shared/types/scenario.types";

const FALLBACK_FIELD_KEY = "field";

export const toFieldKey = (label: string, existing: SetupInputField[]): string => {
  const base =
    label
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "") || FALLBACK_FIELD_KEY;
  const takenKeys = new Set(existing.map((field) => field.key));
  let candidate = base;
  for (let suffix = 2; takenKeys.has(candidate); suffix += 1) {
    candidate = `${base}_${suffix}`;
  }
  return candidate;
};

const buildOptions = (labels: string[]): SetupInputOption[] =>
  labels.map((label) => ({
    id: crypto.randomUUID(),
    label,
    value: label.toLowerCase().replace(/[^a-z0-9]+/g, "_"),
  }));

export const buildQuickAddField = (
  quickAdd: SetupQuickAdd,
  existing: SetupInputField[],
): SetupInputField => {
  const options = buildOptions(quickAdd.options);
  const defaultOption = options.find((option) => option.label === quickAdd.defaultOption);
  return {
    id: crypto.randomUUID(),
    key: toFieldKey(quickAdd.label, existing),
    label: quickAdd.label,
    type: quickAdd.type,
    required: false,
    options,
    defaultValue: defaultOption?.value ?? "",
  };
};

export const buildCustomField = (existing: SetupInputField[]): SetupInputField => ({
  id: crypto.randomUUID(),
  key: toFieldKey("Your own", existing),
  label: "",
  type: "text",
  required: false,
  options: [],
  defaultValue: "",
});

export const hasQuickAdd = (fields: SetupInputField[], quickAdd: SetupQuickAdd): boolean =>
  fields.some((field) => field.label === quickAdd.label);

export const hasNameField = (fields: SetupInputField[]): boolean =>
  fields.some((field) => field.is_character_name);

export const updateField = (
  fields: SetupInputField[],
  fieldId: string,
  updates: Partial<SetupInputField>,
): SetupInputField[] =>
  fields.map((field) => (field.id === fieldId ? { ...field, ...updates } : field));

export const removeField = (fields: SetupInputField[], fieldId: string): SetupInputField[] =>
  fields.filter((field) => field.id !== fieldId);

export const addOption = (field: SetupInputField): SetupInputOption[] => [
  ...field.options,
  ...buildOptions([`Choice ${field.options.length + 1}`]),
];

export const renameOption = (
  options: SetupInputOption[],
  optionId: string,
  label: string,
): SetupInputOption[] =>
  options.map((option) =>
    option.id === optionId
      ? { ...option, label, value: label.toLowerCase().replace(/[^a-z0-9]+/g, "_") }
      : option,
  );
