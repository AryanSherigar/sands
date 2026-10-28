import type { GuideStepDefinition, GuideStepId } from "../constants/guideSteps";
import { getAllGuideSteps, getGuideSteps } from "./guideStepsFor";

export const getGuideStep = (stepId: GuideStepId): GuideStepDefinition => {
  const step = getAllGuideSteps().find((candidate) => candidate.id === stepId);
  if (!step) throw new Error(`Unknown guide step: ${stepId}`);
  return step;
};

export const getGuideStepName = (stepNumber: number, isAdvanced: boolean): string | null =>
  getGuideSteps(isAdvanced).find((step) => step.number === stepNumber)?.name ?? null;
