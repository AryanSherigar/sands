import { ADVANCED_GUIDE_STEPS } from "../constants/advancedSteps";
import {
  BASE_GUIDE_STEPS,
  type GuideStepDefinition,
  type GuideStepId,
} from "../constants/guideSteps";

const ADVANCED_STEP_IDS: ReadonlySet<GuideStepId> = new Set(
  ADVANCED_GUIDE_STEPS.map((step) => step.id),
);

const renumber = (steps: readonly GuideStepDefinition[]): readonly GuideStepDefinition[] =>
  steps.map((step, index) => ({ ...step, number: index + 1 }));

const FINISH_INDEX = BASE_GUIDE_STEPS.length - 1;

const BASE_STEPS = renumber(BASE_GUIDE_STEPS);
const ADVANCED_STEPS = renumber([
  ...BASE_GUIDE_STEPS.slice(0, FINISH_INDEX),
  ...ADVANCED_GUIDE_STEPS,
  BASE_GUIDE_STEPS[FINISH_INDEX],
]);

export const getGuideSteps = (isAdvanced: boolean): readonly GuideStepDefinition[] =>
  isAdvanced ? ADVANCED_STEPS : BASE_STEPS;

export const getGuideStepCount = (isAdvanced: boolean): number =>
  getGuideSteps(isAdvanced).length;

export const isAdvancedStepId = (stepId: GuideStepId): boolean => ADVANCED_STEP_IDS.has(stepId);

export const getAllGuideSteps = (): readonly GuideStepDefinition[] => ADVANCED_STEPS;

export const remapGuideStep = (
  stepNumber: number,
  wasAdvanced: boolean,
  isAdvanced: boolean,
): number => {
  const from = getGuideSteps(wasAdvanced);
  const to = getGuideSteps(isAdvanced);
  const current = from[Math.min(from.length, Math.max(1, stepNumber)) - 1];
  const match = to.find((step) => step.id === current.id);
  if (match) return match.number;
  return to.find((step) => step.id === "opening")?.number ?? 1;
};

export const clampGuideStep = (stepNumber: number, isAdvanced: boolean): number => {
  const steps = getGuideSteps(isAdvanced);
  if (stepNumber < 1) return 1;
  if (stepNumber <= steps.length) return stepNumber;
  return steps.find((step) => step.id === "opening")?.number ?? steps.length;
};
