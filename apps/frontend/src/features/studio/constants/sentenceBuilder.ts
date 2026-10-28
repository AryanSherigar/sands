import type { SelectOption } from "@/shared/components/ui/Select";
import type { ValueKind } from "../types/sentence.types";

export const MAX_SENTENCE_ROWS = 6;
export const NEW_VALUE_OPTION = "__new_tracked_value__";
export const NEW_VALUE_LABEL = "+ New tracked value";
export const NO_SELECTION = "";
export const VALUE_PLACEHOLDER = "Choose a value";
export const COMPARISON_PLACEHOLDER = "Choose…";
export const ADVANCED_LOGIC_MESSAGE = "This uses advanced logic — edit in full editor.";
export const OPEN_FULL_EDITOR_LABEL = "Edit in full editor";
export const NEW_VALUE_FAILED_MESSAGE = "Couldn't add the value. Try again.";
export const TRACKED_GROUP_LABEL = "Tracked values";
export const CARD_GROUP_LABEL = "Card values";
export const GUARD_ROW_LABEL = "While";
export const MUST_ROW_LABEL = "Always";

export const JOINER_OPTIONS: SelectOption[] = [
  { value: "and", label: "and" },
  { value: "or", label: "or" },
];

export const NEW_VALUE_KIND_OPTIONS: Array<SelectOption & { value: ValueKind }> = [
  { value: "number", label: "Number" },
  { value: "boolean", label: "Yes / no" },
  { value: "enum", label: "Choice" },
];

export const NEW_NUMBER_DEFAULTS = { initial: 0, min: 0, max: 10 } as const;
export const COMPARE_TO_LABEL = "Compare to";
export const COMPARE_TO_OPTIONS: SelectOption[] = [
  { value: "amount", label: "a number" },
  { value: "value", label: "another value" },
];
