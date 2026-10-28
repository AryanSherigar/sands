import {
  CHARACTERS_STEP_NUMBER,
  IDEA_STEP_NUMBER,
  OPENING_STEP_NUMBER,
  PREMISE_STEP_NUMBER,
} from "../constants/finish";
import type { ScenarioResponse } from "../types/scenario.types";
import { countWords } from "./loreDocument";
import { readWorldDocument } from "./worldDocuments";

export type RequiredItemId = "name" | "idea" | "opening";
export type SuggestionId = "premise" | "genre" | "characters";

export interface ChecklistItem<TId extends string> {
  id: TId;
  label: string;
  isDone: boolean;
  fixStep: number;
}

const hasText = (value: string | null | undefined): boolean =>
  Boolean(value && value.trim().length > 0);

export const hasOpeningText = (scenario: ScenarioResponse | null): boolean => {
  if (!scenario) return false;
  if (hasText(scenario.opening_scene)) return true;
  return countWords(readWorldDocument(scenario.world_data, "openingDocument")) > 0;
};

const hasPremiseText = (scenario: ScenarioResponse): boolean =>
  countWords(readWorldDocument(scenario.world_data, "premiseDocument")) > 0 ||
  hasText(scenario.world_data?.premise as string | undefined);

export const getRequiredItems = (
  scenario: ScenarioResponse | null,
): ChecklistItem<RequiredItemId>[] => [
  { id: "name", label: "Name", isDone: hasText(scenario?.title), fixStep: IDEA_STEP_NUMBER },
  { id: "idea", label: "One line idea", isDone: hasText(scenario?.logline), fixStep: IDEA_STEP_NUMBER },
  { id: "opening", label: "Opening", isDone: hasOpeningText(scenario), fixStep: OPENING_STEP_NUMBER },
];

export const getSuggestions = (
  scenario: ScenarioResponse | null,
  cardCount: number,
): ChecklistItem<SuggestionId>[] => [
  {
    id: "premise",
    label: "Premise",
    isDone: scenario ? hasPremiseText(scenario) : false,
    fixStep: PREMISE_STEP_NUMBER,
  },
  {
    id: "genre",
    label: "Kind of story",
    isDone: (scenario?.genre_tags.length ?? 0) > 0,
    fixStep: PREMISE_STEP_NUMBER,
  },
  {
    id: "characters",
    label: "Characters",
    isDone: cardCount > 0,
    fixStep: CHARACTERS_STEP_NUMBER,
  },
];

export const SUGGESTION_HINTS: Record<SuggestionId, string> = {
  premise: "add one for a richer story",
  genre: "pick one so readers can find it",
  characters: "add someone for the player to meet",
};

export const describeMissingRequired = (
  items: ChecklistItem<RequiredItemId>[],
): string | null => {
  const missing = items.filter((item) => !item.isDone).map((item) => item.label);
  return missing.length > 0 ? `To publish, add: ${missing.join(", ")}.` : null;
};
