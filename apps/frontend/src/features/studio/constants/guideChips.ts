import type { SetupInputField } from "@/shared/types/scenario.types";

export const MOOD_CHIPS = [
  "eerie",
  "cozy",
  "tense",
  "funny",
  "epic",
  "sad",
  "hopeful",
  "lonely",
] as const;

export const PRIMARY_GENRE_LABEL = "Primary";

export const NAME_SETUP_FIELD: SetupInputField = {
  id: "setup-name",
  key: "character_name",
  label: "Name",
  type: "text",
  required: true,
  options: [],
  defaultValue: "",
  is_character_name: true,
};

export interface SetupQuickAdd {
  id: string;
  label: string;
  type: SetupInputField["type"];
  options: string[];
  defaultOption?: string;
}

export const SETUP_QUICK_ADDS: readonly SetupQuickAdd[] = [
  {
    id: "pronouns",
    label: "Pronouns",
    type: "single_select",
    options: ["She", "He", "They", "Their own"],
  },
  { id: "looks", label: "Looks", type: "text", options: [] },
  {
    id: "background",
    label: "Background",
    type: "single_select",
    options: ["Background one", "Background two"],
  },
  {
    id: "starting-item",
    label: "Starting item",
    type: "single_select",
    options: ["Item one", "Item two"],
  },
  {
    id: "difficulty",
    label: "Difficulty",
    type: "single_select",
    options: ["Gentle", "Normal", "Harsh"],
    defaultOption: "Normal",
  },
];

export const SETUP_FIELD_TYPE_OPTIONS = [
  { value: "text", label: "Short answer" },
  { value: "textarea", label: "Long answer" },
  { value: "number", label: "Number" },
  { value: "single_select", label: "Pick one" },
  { value: "multi_select", label: "Pick several" },
];
