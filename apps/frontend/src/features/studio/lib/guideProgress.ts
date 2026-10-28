import type { GuideStepId } from "../constants/guideSteps";
import type { GroupedCards } from "./cardGroups";
import { hasOpeningText } from "./finishChecklist";
import { getGuideSteps, isAdvancedStepId } from "./guideStepsFor";
import { countWords } from "./loreDocument";
import { readWorldDocument } from "./worldDocuments";
import type { ScenarioResponse } from "../types/scenario.types";

export type GuideStepStatus = "done" | "current" | "todo";

const hasText = (value: string | null | undefined): boolean =>
  Boolean(value && value.trim().length > 0);

const hasDocumentText = (scenario: ScenarioResponse | null, key: string): boolean =>
  countWords(readWorldDocument(scenario?.world_data, key)) > 0;

const hasWorldCards = (cards: GroupedCards): boolean =>
  cards.places.length + cards.groups.length + cards.things.length + cards.others.length > 0;

export const isStepDone = (
  stepId: GuideStepId,
  scenario: ScenarioResponse | null,
  cards: GroupedCards,
): boolean => {
  switch (stepId) {
    case "idea":
      return hasText(scenario?.logline) && hasText(scenario?.title);
    case "premise":
      return hasDocumentText(scenario, "premiseDocument");
    case "player":
      return cards.player !== null;
    case "characters":
      return cards.characters.length > 0;
    case "world":
      return hasDocumentText(scenario, "worldLoreDocument") || hasWorldCards(cards);
    case "opening":
      return hasOpeningText(scenario);
    case "finish":
      return scenario?.status === "published";
    case "endings":
    case "tracked_values":
    case "rules":
    case "hard_limits":
    case "extras":
      return false;
  }
};

export const getStepStatus = (
  stepNumber: number,
  activeStep: number,
  isDone: boolean,
): GuideStepStatus => {
  if (isDone) return "done";
  return stepNumber === activeStep ? "current" : "todo";
};

export const getFirstUnfinishedStep = (
  scenario: ScenarioResponse | null,
  cards: GroupedCards,
  isAdvanced = false,
): number => {
  const steps = getGuideSteps(isAdvanced);
  const unfinished = steps.find(
    (step) => !isAdvancedStepId(step.id) && !isStepDone(step.id, scenario, cards),
  );
  return unfinished?.number ?? steps.length;
};
